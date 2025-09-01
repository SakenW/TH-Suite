"""TransHub Tools Protocol Validation.

Validation utilities and helpers for protocol schemas.
"""

from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .schemas import (
    BuildRequestSchema,
    ExtractRequestSchema,
    InventorySchema,
    ScanRequestSchema,
    SegmentSchema,
)

T = TypeVar("T", bound=BaseModel)


class ValidationResult:
    """Result of a validation operation."""

    def __init__(
        self, success: bool, data: Any | None = None, errors: list[str] | None = None
    ):
        self.success = success
        self.data = data
        self.errors = errors or []

    def __bool__(self) -> bool:
        return self.success

    def __repr__(self) -> str:
        if self.success:
            return f"ValidationResult(success=True, data={type(self.data).__name__})"
        else:
            return f"ValidationResult(success=False, errors={self.errors})"


class ProtocolValidator:
    """Protocol validation utilities."""

    @staticmethod
    def validate_schema(
        schema_class: type[T], data: dict[str, Any]
    ) -> ValidationResult:
        """Validate data against a Pydantic schema."""
        try:
            validated_data = schema_class(**data)
            return ValidationResult(success=True, data=validated_data)
        except ValidationError as e:
            errors = [
                f"{err['loc'][0] if err['loc'] else 'root'}: {err['msg']}"
                for err in e.errors()
            ]
            return ValidationResult(success=False, errors=errors)
        except Exception as e:
            return ValidationResult(success=False, errors=[str(e)])

    @staticmethod
    def validate_scan_request(data: dict[str, Any]) -> ValidationResult:
        """Validate scan request data."""
        return ProtocolValidator.validate_schema(ScanRequestSchema, data)

    @staticmethod
    def validate_extract_request(data: dict[str, Any]) -> ValidationResult:
        """Validate extract request data."""
        return ProtocolValidator.validate_schema(ExtractRequestSchema, data)

    @staticmethod
    def validate_build_request(data: dict[str, Any]) -> ValidationResult:
        """Validate build request data."""
        return ProtocolValidator.validate_schema(BuildRequestSchema, data)

    @staticmethod
    def validate_inventory(data: dict[str, Any]) -> ValidationResult:
        """Validate inventory data."""
        return ProtocolValidator.validate_schema(InventorySchema, data)

    @staticmethod
    def validate_segments(data: list[dict[str, Any]]) -> ValidationResult:
        """Validate a list of segment data."""
        try:
            validated_segments = []
            errors = []

            for i, segment_data in enumerate(data):
                try:
                    segment = SegmentSchema(**segment_data)
                    validated_segments.append(segment)
                except ValidationError as e:
                    segment_errors = [
                        f"Segment {i}: {err['loc'][0] if err['loc'] else 'root'}: {err['msg']}"
                        for err in e.errors()
                    ]
                    errors.extend(segment_errors)

            if errors:
                return ValidationResult(success=False, errors=errors)

            return ValidationResult(success=True, data=validated_segments)
        except Exception as e:
            return ValidationResult(success=False, errors=[str(e)])


class DataConverter:
    """Data conversion utilities."""

    @staticmethod
    def to_dict(model: BaseModel, exclude_none: bool = True) -> dict[str, Any]:
        """Convert a Pydantic model to dictionary."""
        return model.dict(exclude_none=exclude_none)

    @staticmethod
    def to_json(
        model: BaseModel, exclude_none: bool = True, indent: int | None = None
    ) -> str:
        """Convert a Pydantic model to JSON string."""
        return model.json(exclude_none=exclude_none, indent=indent)

    @staticmethod
    def from_dict(schema_class: type[T], data: dict[str, Any]) -> T:
        """Create a Pydantic model from dictionary."""
        return schema_class(**data)

    @staticmethod
    def from_json(schema_class: type[T], json_str: str) -> T:
        """Create a Pydantic model from JSON string."""
        return schema_class.parse_raw(json_str)

    @staticmethod
    def convert_datetime(dt: datetime | str | None) -> datetime | None:
        """Convert various datetime formats to datetime object."""
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt
        if isinstance(dt, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except ValueError:
                try:
                    # Try common formats
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]:
                        try:
                            return datetime.strptime(dt, fmt)
                        except ValueError:
                            continue
                    raise ValueError(f"Unable to parse datetime: {dt}")
                except ValueError:
                    return None
        return None

    @staticmethod
    def normalize_locale(locale: str) -> str:
        """Normalize locale string to standard format."""
        if not locale:
            return "en_us"

        # Convert to lowercase and replace hyphens with underscores
        normalized = locale.lower().replace("-", "_")

        # Handle common variations
        locale_map = {
            "en": "en_us",
            "zh": "zh_cn",
            "zh_hans": "zh_cn",
            "zh_hant": "zh_tw",
            "ja": "ja_jp",
            "ko": "ko_kr",
            "fr": "fr_fr",
            "de": "de_de",
            "es": "es_es",
            "it": "it_it",
            "pt": "pt_br",
            "ru": "ru_ru",
        }

        return locale_map.get(normalized, normalized)

    @staticmethod
    def normalize_modid(modid: str) -> str:
        """Normalize mod ID to standard format."""
        if not modid:
            return "unknown"

        # Convert to lowercase and replace spaces/special chars with underscores
        import re

        normalized = re.sub(r"[^a-z0-9_]", "_", modid.lower())

        # Remove multiple consecutive underscores
        normalized = re.sub(r"_+", "_", normalized)

        # Remove leading/trailing underscores
        normalized = normalized.strip("_")

        return normalized or "unknown"


class ProtocolConstants:
    """Protocol constants and defaults."""

    # Default values
    DEFAULT_LOCALE = "en_us"
    DEFAULT_MODID = "minecraft"
    DEFAULT_OUTPUT_FORMAT = "json"

    # Supported file formats
    SUPPORTED_FORMATS = ["json", "lang", "toml", "cfg"]

    # Common locales
    COMMON_LOCALES = [
        "en_us",
        "zh_cn",
        "zh_tw",
        "ja_jp",
        "ko_kr",
        "fr_fr",
        "de_de",
        "es_es",
        "it_it",
        "pt_br",
        "ru_ru",
        "ar_sa",
        "hi_in",
        "th_th",
        "vi_vn",
    ]

    # File size limits (bytes)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_INVENTORY_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_SEGMENTS_COUNT = 1000000  # 1M segments

    # Validation patterns
    LOCALE_PATTERN = r"^[a-z]{2}_[a-z]{2}$"
    MODID_PATTERN = r"^[a-z0-9_]+$"
    TRANSLATION_KEY_PATTERN = r"^[a-zA-Z0-9._-]+$"

    @classmethod
    def is_valid_locale(cls, locale: str) -> bool:
        """Check if locale format is valid."""
        import re

        return bool(re.match(cls.LOCALE_PATTERN, locale))

    @classmethod
    def is_valid_modid(cls, modid: str) -> bool:
        """Check if mod ID format is valid."""
        import re

        return bool(re.match(cls.MODID_PATTERN, modid))

    @classmethod
    def is_valid_translation_key(cls, key: str) -> bool:
        """Check if translation key format is valid."""
        import re

        return bool(re.match(cls.TRANSLATION_KEY_PATTERN, key))

    @classmethod
    def is_supported_format(cls, format_name: str) -> bool:
        """Check if file format is supported."""
        return format_name.lower() in cls.SUPPORTED_FORMATS


# Convenience functions


def validate_request(request_type: str, data: dict[str, Any]) -> ValidationResult:
    """Validate request data based on type."""
    validators = {
        "scan": ProtocolValidator.validate_scan_request,
        "extract": ProtocolValidator.validate_extract_request,
        "build": ProtocolValidator.validate_build_request,
    }

    validator = validators.get(request_type)
    if not validator:
        return ValidationResult(
            success=False, errors=[f"Unknown request type: {request_type}"]
        )

    return validator(data)


def normalize_data(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize common data fields."""
    normalized = data.copy()

    # Normalize locale if present
    if "locale" in normalized:
        normalized["locale"] = DataConverter.normalize_locale(normalized["locale"])

    if "locales" in normalized and isinstance(normalized["locales"], list):
        normalized["locales"] = [
            DataConverter.normalize_locale(loc) for loc in normalized["locales"]
        ]

    # Normalize modid if present
    if "modid" in normalized:
        normalized["modid"] = DataConverter.normalize_modid(normalized["modid"])

    # Convert datetime strings
    for field in ["created_at", "started_at", "completed_at", "timestamp"]:
        if field in normalized:
            normalized[field] = DataConverter.convert_datetime(normalized[field])

    return normalized
