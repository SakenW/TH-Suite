"""TH Suite MC L10n extract service for processing language files."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import structlog

if TYPE_CHECKING:
    from packages.core.database import SQLCipherDatabase

from packages.backend_kit.websocket import send_log_message, send_progress_update
from packages.core.errors import ProcessingError, ValidationError
from packages.core.models import ExtractRequest, Inventory, InventoryItem, Segment
from packages.core.state import State, StateMachine
from packages.parsers import get_parser_for_file


class ExtractService:
    """Service for extracting translations from language files."""

    def __init__(
        self,
        logger: structlog.BoundLogger,
        state_machine: StateMachine,
        database: Optional["SQLCipherDatabase"] = None,
    ):
        self.logger = logger
        self.state_machine = state_machine
        self.database = database

    async def extract_translations(
        self, job_id: str, request: ExtractRequest, context: dict
    ) -> None:
        """Extract translations from language files.

        Args:
            job_id: Unique job identifier
            request: Extract request parameters
            context: Job execution context
        """
        logger = self.logger.bind(job_id=job_id)

        try:
            logger.info(
                "Starting translation extraction", inventory_file=request.inventory_file
            )
            await send_log_message(job_id, "info", "Starting translation extraction")
            await send_progress_update(job_id, 0, "Loading inventory...")

            # Load inventory
            inventory = await self._load_inventory(request.inventory_file, job_id)

            # Filter items by locales if specified
            filtered_items = self._filter_items_by_locales(
                inventory.items, request.locales
            )

            # Extract segments from files
            segments = await self._extract_segments(filtered_items, request, job_id)

            # Validate segments if requested
            if request.validate_keys:
                segments = await self._validate_segments(segments, job_id)

            # Save segments to file
            output_file = request.output_file or "segments.json"
            await self._save_segments(segments, output_file, job_id)

            # Update context with results
            context.update(
                {
                    "result": {
                        "segments_file": output_file,
                        "total_segments": len(segments),
                        "processed_files": len(filtered_items),
                        "locales": list(set(item.locale for item in filtered_items)),
                    },
                    "message": "Extraction completed successfully",
                }
            )

            # Transition to completed state
            self.state_machine.transition(State.COMPLETED, context)

            await send_progress_update(job_id, 100, "Extraction completed successfully")
            await send_log_message(
                job_id,
                "info",
                f"Extraction completed. Generated {len(segments)} segments",
            )

            logger.info(
                "Extraction completed successfully",
                total_segments=len(segments),
                processed_files=len(filtered_items),
                output_file=output_file,
            )

        except Exception as e:
            logger.error("Extraction failed", error=str(e), exc_info=True)

            # Update context with error
            context.update({"error": str(e), "message": f"Extraction failed: {str(e)}"})

            # Transition to failed state
            self.state_machine.transition(State.FAILED, context)

            await send_log_message(job_id, "error", f"Extraction failed: {str(e)}")
            await send_progress_update(job_id, 0, f"Extraction failed: {str(e)}")

    async def _load_inventory(self, inventory_file: str, job_id: str) -> Inventory:
        """Load inventory from JSON file."""
        logger = self.logger.bind(job_id=job_id, phase="load_inventory")

        try:
            inventory_path = Path(inventory_file)
            if not inventory_path.exists():
                raise ValidationError(
                    f"Inventory file does not exist: {inventory_file}"
                )

            with open(inventory_path, encoding="utf-8") as f:
                data = json.load(f)

            # Convert to inventory items
            items = []
            for item_data in data.get("items", []):
                item = InventoryItem(
                    modid=item_data["modid"],
                    locale=item_data["locale"],
                    path=item_data["path"],
                    hash=item_data["hash"],
                    format=item_data["format"],
                    size=item_data.get("size", 0),
                )
                items.append(item)

            inventory = Inventory(items=items)

            logger.info(
                "Inventory loaded successfully",
                total_items=len(items),
                unique_locales=len(inventory.get_locales()),
                unique_mods=len(inventory.get_modids()),
            )

            return inventory

        except Exception as e:
            logger.error("Failed to load inventory", error=str(e))
            raise ProcessingError(f"Failed to load inventory: {str(e)}")

    def _filter_items_by_locales(
        self, items: list[InventoryItem], locales: list[str] | None
    ) -> list[InventoryItem]:
        """Filter inventory items by specified locales."""
        if not locales:
            return items

        locale_set = set(locales)
        filtered_items = [item for item in items if item.locale in locale_set]

        self.logger.info(
            "Filtered items by locales",
            original_count=len(items),
            filtered_count=len(filtered_items),
            target_locales=locales,
        )

        return filtered_items

    async def _extract_segments(
        self, items: list[InventoryItem], request: ExtractRequest, job_id: str
    ) -> list[Segment]:
        """Extract translation segments from language files."""
        logger = self.logger.bind(job_id=job_id, phase="extract_segments")

        await send_progress_update(job_id, 20, "Extracting translation segments...")

        segments = []
        total_items = len(items)

        for i, item in enumerate(items):
            item_logger = logger.bind(
                modid=item.modid, locale=item.locale, file_path=item.path
            )

            try:
                # Get appropriate parser for the file
                parser = get_parser_for_file(item.path)
                if not parser:
                    item_logger.warning(
                        "No parser available for file format", format=item.format
                    )
                    continue

                # Check if file still exists
                file_path = Path(item.path)
                if not file_path.exists():
                    item_logger.warning("File no longer exists, skipping")
                    continue

                # Parse the file
                parse_result = parser.parse(str(file_path))
                if not parse_result.success:
                    item_logger.warning(
                        "Failed to parse file",
                        error=parse_result.error,
                        warnings=parse_result.warnings,
                    )
                    continue

                # Convert segments to our format
                for segment in parse_result.segments:
                    new_segment = Segment(
                        modid=item.modid,
                        locale=item.locale,
                        key=segment.key,
                        value=segment.value,
                        context=segment.context,
                        file_path=item.path,
                        line_number=segment.line_number,
                    )
                    segments.append(new_segment)

                item_logger.debug(
                    "Extracted segments from file",
                    segment_count=len(parse_result.segments),
                )

            except Exception as e:
                item_logger.warning(
                    "Failed to extract segments from file", error=str(e)
                )
                # Continue with other files
                continue

            # Update progress
            progress = 20 + (i + 1) / total_items * 60
            await send_progress_update(
                job_id,
                int(progress),
                f"Processed file {i + 1}/{total_items}: {item.modid}/{item.locale}",
            )

        logger.info(
            "Segment extraction completed",
            total_segments=len(segments),
            processed_files=total_items,
        )

        return segments

    async def _validate_segments(
        self, segments: list[Segment], job_id: str
    ) -> list[Segment]:
        """Validate translation segments for consistency."""
        logger = self.logger.bind(job_id=job_id, phase="validate_segments")

        await send_progress_update(job_id, 85, "Validating translation segments...")

        # Group segments by key
        key_groups: dict[str, list[Segment]] = {}
        for segment in segments:
            key = f"{segment.modid}:{segment.key}"
            if key not in key_groups:
                key_groups[key] = []
            key_groups[key].append(segment)

        # Check for inconsistencies
        issues_found = 0
        valid_segments = []

        for key, group in key_groups.items():
            # Check if all segments with the same key have consistent values across locales
            base_segment = group[0]

            # For now, just add all segments (validation can be enhanced later)
            valid_segments.extend(group)

            # Log potential issues
            if len(group) > 1:
                locales = [s.locale for s in group]
                if len(set(locales)) != len(locales):
                    logger.warning(
                        "Duplicate key found in same locale",
                        key=base_segment.key,
                        modid=base_segment.modid,
                        locales=locales,
                    )
                    issues_found += 1

        if issues_found > 0:
            logger.warning(
                "Validation completed with issues",
                total_issues=issues_found,
                total_segments=len(valid_segments),
            )
        else:
            logger.info(
                "Validation completed successfully", total_segments=len(valid_segments)
            )

        return valid_segments

    async def _save_segments(
        self, segments: list[Segment], output_file: str, job_id: str
    ) -> None:
        """Save segments to JSON file."""
        logger = self.logger.bind(job_id=job_id, phase="save_segments")

        await send_progress_update(job_id, 90, "Saving translation segments...")

        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert segments to dict and save as JSON
            segments_data = {
                "version": "1.0",
                "total_segments": len(segments),
                "segments": [segment.dict() for segment in segments],
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(segments_data, f, indent=2, ensure_ascii=False)

            logger.info(
                "Segments saved successfully",
                output_file=output_file,
                file_size=output_path.stat().st_size,
                total_segments=len(segments),
            )

        except Exception as e:
            logger.error(
                "Failed to save segments", error=str(e), output_file=output_file
            )
            raise ProcessingError(f"Failed to save segments: {str(e)}")
