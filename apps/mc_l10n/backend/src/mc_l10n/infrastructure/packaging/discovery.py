"""TH Suite MC L10n discovery service for finding Minecraft mods and language files."""

import json
import re
from pathlib import Path

import structlog
from domain.models import (
    MinecraftLanguageFile,
    MinecraftMod,
    MinecraftModPack,
    MinecraftVersion,
    ModLoader,
)


class MinecraftDiscovery:
    """Service for discovering Minecraft mods and language files."""

    # Common Minecraft language file patterns
    LANG_FILE_PATTERNS = [
        r".*\.lang$",  # Legacy .lang files
        r".*\.json$",  # Modern JSON language files
    ]

    # Common mod directory patterns
    MOD_DIR_PATTERNS = [
        r"mods?",
        r".*mod.*",
        r"assets",
        r"src/main/resources",
    ]

    # Locale pattern (e.g., en_us, zh_cn, etc.)
    LOCALE_PATTERN = re.compile(r"([a-z]{2}_[a-z]{2}|[a-z]{2})")

    # Mod ID pattern
    MOD_ID_PATTERN = re.compile(r"[a-z0-9_-]+")

    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger

    async def discover_mod_pack(
        self,
        directory: Path,
        recursive: bool = True,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> MinecraftModPack:
        """Discover a mod pack in the given directory.

        Args:
            directory: Root directory to search
            recursive: Whether to search recursively
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude

        Returns:
            MinecraftModPack with discovered mods
        """
        logger = self.logger.bind(directory=str(directory))
        logger.info("Starting mod pack discovery")

        # Create mod pack
        mod_pack = MinecraftModPack(name=directory.name, path=directory)

        # Detect mod loader and MC version
        mod_pack.loader = await self._detect_mod_loader(directory)
        mod_pack.mc_version = await self._detect_mc_version(directory)

        # Find all language files
        lang_files = await self._find_language_files(
            directory, recursive, include_patterns, exclude_patterns
        )

        # Group language files by mod
        mods_dict = await self._group_files_by_mod(lang_files)

        # Create mod objects
        for mod_id, files in mods_dict.items():
            mod = await self._create_mod_from_files(mod_id, files)
            mod_pack.add_mod(mod)

        logger.info(
            "Mod pack discovery completed",
            total_mods=len(mod_pack.mods),
            total_files=mod_pack.get_total_language_files(),
            loader=mod_pack.loader.value if mod_pack.loader else None,
            mc_version=mod_pack.mc_version.value if mod_pack.mc_version else None,
        )

        return mod_pack

    async def _detect_mod_loader(self, directory: Path) -> ModLoader | None:
        """Detect the mod loader used in this directory."""
        # Check for common mod loader files
        loader_indicators = {
            ModLoader.FORGE: ["mods.toml", "META-INF/mods.toml", "mcmod.info"],
            ModLoader.FABRIC: ["fabric.mod.json", "quilt.mod.json"],
            ModLoader.QUILT: ["quilt.mod.json"],
            ModLoader.NEOFORGE: ["neoforge.mods.toml", "META-INF/neoforge.mods.toml"],
        }

        for loader, indicators in loader_indicators.items():
            for indicator in indicators:
                if (directory / indicator).exists():
                    return loader

                # Also check in subdirectories
                for path in directory.rglob(indicator):
                    if path.exists():
                        return loader

        return None

    async def _detect_mc_version(self, directory: Path) -> MinecraftVersion | None:
        """Detect Minecraft version category."""
        # This is a simplified detection - in practice, you'd parse mod metadata
        # For now, assume modern if we find JSON lang files, legacy if .lang files

        has_json_lang = any(directory.rglob("*.json"))
        has_lang_files = any(directory.rglob("*.lang"))

        if has_json_lang and not has_lang_files:
            return MinecraftVersion.MODERN
        elif has_lang_files and not has_json_lang:
            return MinecraftVersion.LEGACY
        elif has_json_lang and has_lang_files:
            return MinecraftVersion.MODERN  # Mixed, assume modern

        return None

    async def _find_language_files(
        self,
        directory: Path,
        recursive: bool,
        include_patterns: list[str] | None,
        exclude_patterns: list[str] | None,
    ) -> list[Path]:
        """Find all language files in the directory."""
        logger = self.logger.bind(phase="find_files")

        # Compile patterns
        include_regexes = []
        if include_patterns:
            include_regexes = [
                re.compile(pattern, re.IGNORECASE) for pattern in include_patterns
            ]
        else:
            include_regexes = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in self.LANG_FILE_PATTERNS
            ]

        exclude_regexes = []
        if exclude_patterns:
            exclude_regexes = [
                re.compile(pattern, re.IGNORECASE) for pattern in exclude_patterns
            ]

        # Find files
        lang_files = []
        search_pattern = "**/*" if recursive else "*"

        for file_path in directory.glob(search_pattern):
            if not file_path.is_file():
                continue

            file_str = str(file_path)

            # Check include patterns
            if include_regexes:
                if not any(regex.search(file_str) for regex in include_regexes):
                    continue

            # Check exclude patterns
            if exclude_regexes:
                if any(regex.search(file_str) for regex in exclude_regexes):
                    continue

            # Additional check: must look like a language file
            if self._is_language_file(file_path):
                lang_files.append(file_path)

        logger.info(f"Found {len(lang_files)} language files")
        return lang_files

    def _is_language_file(self, file_path: Path) -> bool:
        """Check if a file looks like a language file."""
        # Check file extension
        if file_path.suffix not in [".json", ".lang"]:
            return False

        # Check if filename contains locale pattern
        filename = file_path.stem
        if self.LOCALE_PATTERN.fullmatch(filename):
            return True

        # Check if it's in a lang directory
        if "lang" in [p.name.lower() for p in file_path.parents]:
            return True

        # Check if path contains assets structure
        path_parts = file_path.parts
        if "assets" in path_parts and "lang" in path_parts:
            return True

        return False

    async def _group_files_by_mod(
        self, lang_files: list[Path]
    ) -> dict[str, list[Path]]:
        """Group language files by mod ID."""
        logger = self.logger.bind(phase="group_by_mod")

        mods_dict = {}

        for file_path in lang_files:
            mod_id = await self._extract_mod_id(file_path)

            if mod_id not in mods_dict:
                mods_dict[mod_id] = []

            mods_dict[mod_id].append(file_path)

        logger.info(f"Grouped files into {len(mods_dict)} mods")
        return mods_dict

    async def _extract_mod_id(self, file_path: Path) -> str:
        """Extract mod ID from file path."""
        # Try to extract from assets structure: assets/modid/lang/locale.json
        path_parts = file_path.parts

        if "assets" in path_parts:
            assets_index = path_parts.index("assets")
            if assets_index + 1 < len(path_parts):
                potential_mod_id = path_parts[assets_index + 1]
                if self.MOD_ID_PATTERN.fullmatch(potential_mod_id):
                    return potential_mod_id

        # Try to extract from parent directory names
        for parent in file_path.parents:
            parent_name = parent.name.lower()
            if self.MOD_ID_PATTERN.fullmatch(parent_name) and parent_name not in [
                "lang",
                "assets",
                "resources",
            ]:
                return parent_name

        # Fallback: use the directory containing the file
        return file_path.parent.name.lower() or "unknown"

    async def _create_mod_from_files(
        self, mod_id: str, files: list[Path]
    ) -> MinecraftMod:
        """Create a mod object from its language files."""
        if not files:
            raise ValueError(f"No files provided for mod {mod_id}")

        # Use the first file's parent as mod path
        mod_path = files[0].parent

        # Try to find a better mod path (e.g., the assets/modid directory)
        for file_path in files:
            path_parts = file_path.parts
            if "assets" in path_parts:
                assets_index = path_parts.index("assets")
                if assets_index + 1 < len(path_parts):
                    potential_path = Path(*path_parts[: assets_index + 2])
                    if potential_path.exists():
                        mod_path = potential_path
                        break

        # Create mod
        mod = MinecraftMod(
            mod_id=mod_id, name=mod_id.replace("_", " ").title(), path=mod_path
        )

        # Add language files
        for file_path in files:
            locale = self._extract_locale(file_path)
            format_type = file_path.suffix[1:]  # Remove the dot

            lang_file = MinecraftLanguageFile(
                path=file_path, locale=locale, format=format_type, mod_id=mod_id
            )

            mod.add_language_file(lang_file)

        # Try to load mod metadata
        await self._load_mod_metadata(mod)

        return mod

    def _extract_locale(self, file_path: Path) -> str:
        """Extract locale from file path."""
        # Try filename first
        filename = file_path.stem
        match = self.LOCALE_PATTERN.fullmatch(filename)
        if match:
            return match.group(0)

        # Try parent directory names
        for parent in file_path.parents:
            match = self.LOCALE_PATTERN.fullmatch(parent.name)
            if match:
                return match.group(0)

        # Fallback
        return filename or "unknown"

    async def _load_mod_metadata(self, mod: MinecraftMod) -> None:
        """Load mod metadata from common metadata files."""
        metadata_files = [
            "mods.toml",
            "META-INF/mods.toml",
            "mcmod.info",
            "fabric.mod.json",
            "quilt.mod.json",
        ]

        for metadata_file in metadata_files:
            metadata_path = mod.path / metadata_file
            if metadata_path.exists():
                try:
                    await self._parse_metadata_file(mod, metadata_path)
                    break
                except Exception as e:
                    self.logger.warning(
                        "Failed to parse metadata file",
                        mod_id=mod.mod_id,
                        metadata_file=str(metadata_path),
                        error=str(e),
                    )

    async def _parse_metadata_file(
        self, mod: MinecraftMod, metadata_path: Path
    ) -> None:
        """Parse a mod metadata file."""
        if metadata_path.suffix == ".json":
            # Parse JSON metadata (Fabric/Quilt)
            with open(metadata_path, encoding="utf-8") as f:
                data = json.load(f)

            mod.name = data.get("name", mod.name)
            mod.version = data.get("version")
            mod.metadata.update(data)

        elif metadata_path.suffix == ".toml":
            # Parse TOML metadata (Forge/NeoForge)
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError:
                    self.logger.warning(
                        "TOML library not available, skipping TOML metadata"
                    )
                    return

            with open(metadata_path, "rb") as f:
                data = tomllib.load(f)

            # Extract mod info from TOML structure
            mods = data.get("mods", [])
            if mods:
                mod_data = mods[0]  # Take first mod
                mod.name = mod_data.get("displayName", mod.name)
                mod.version = mod_data.get("version")
                mod.metadata.update(mod_data)

        else:
            # Handle other formats if needed
            pass
