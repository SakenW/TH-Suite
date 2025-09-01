"""TH Suite MC L10n domain models for Minecraft-specific entities."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class MinecraftVersion(Enum):
    """Minecraft version categories."""

    LEGACY = "legacy"  # 1.12.2 and below
    MODERN = "modern"  # 1.13+
    LATEST = "latest"  # 1.19+


class ModLoader(Enum):
    """Minecraft mod loader types."""

    FORGE = "forge"
    FABRIC = "fabric"
    QUILT = "quilt"
    NEOFORGE = "neoforge"
    VANILLA = "vanilla"


@dataclass
class MinecraftLanguageFile:
    """Represents a Minecraft language file."""

    path: Path
    locale: str
    format: str  # json, lang, etc.
    mod_id: str | None = None
    size: int = 0
    last_modified: datetime | None = None

    def __post_init__(self):
        if self.path.exists():
            stat = self.path.stat()
            self.size = stat.st_size
            self.last_modified = datetime.fromtimestamp(stat.st_mtime)


@dataclass
class MinecraftMod:
    """Represents a Minecraft mod with its language files."""

    mod_id: str
    name: str | None
    path: Path
    version: str | None = None
    loader: ModLoader | None = None
    mc_version: MinecraftVersion | None = None
    language_files: list[MinecraftLanguageFile] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_locales(self) -> list[str]:
        """Get all available locales for this mod."""
        return list(set(lf.locale for lf in self.language_files))

    def get_language_file(self, locale: str) -> MinecraftLanguageFile | None:
        """Get language file for specific locale."""
        for lf in self.language_files:
            if lf.locale == locale:
                return lf
        return None

    def add_language_file(self, lang_file: MinecraftLanguageFile) -> None:
        """Add a language file to this mod."""
        # Set mod_id if not already set
        if not lang_file.mod_id:
            lang_file.mod_id = self.mod_id

        # Check if file already exists
        existing = self.get_language_file(lang_file.locale)
        if existing:
            # Replace existing file
            self.language_files.remove(existing)

        self.language_files.append(lang_file)


@dataclass
class MinecraftModPack:
    """Represents a collection of Minecraft mods (mod pack)."""

    name: str
    path: Path
    mods: list[MinecraftMod] = field(default_factory=list)
    loader: ModLoader | None = None
    mc_version: MinecraftVersion | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_mod(self, mod_id: str) -> MinecraftMod | None:
        """Get mod by ID."""
        for mod in self.mods:
            if mod.mod_id == mod_id:
                return mod
        return None

    def add_mod(self, mod: MinecraftMod) -> None:
        """Add a mod to this pack."""
        existing = self.get_mod(mod.mod_id)
        if existing:
            # Merge language files
            for lang_file in mod.language_files:
                existing.add_language_file(lang_file)
            # Update metadata
            existing.metadata.update(mod.metadata)
        else:
            self.mods.append(mod)

    def get_all_locales(self) -> list[str]:
        """Get all available locales across all mods."""
        locales = set()
        for mod in self.mods:
            locales.update(mod.get_locales())
        return sorted(list(locales))

    def get_mod_ids(self) -> list[str]:
        """Get all mod IDs in this pack."""
        return [mod.mod_id for mod in self.mods]

    def get_total_language_files(self) -> int:
        """Get total number of language files across all mods."""
        return sum(len(mod.language_files) for mod in self.mods)


@dataclass
class MinecraftResourcePack:
    """Represents a Minecraft resource pack."""

    name: str
    path: Path
    pack_format: int
    description: str
    language_files: list[MinecraftLanguageFile] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_pack_mcmeta(self) -> dict[str, Any]:
        """Generate pack.mcmeta content."""
        return {
            "pack": {"pack_format": self.pack_format, "description": self.description}
        }

    def add_language_file(self, lang_file: MinecraftLanguageFile) -> None:
        """Add a language file to this resource pack."""
        self.language_files.append(lang_file)

    def get_locales(self) -> list[str]:
        """Get all available locales in this resource pack."""
        return list(set(lf.locale for lf in self.language_files))


@dataclass
class MinecraftProject:
    """Represents a complete Minecraft translation project."""

    name: str
    path: Path
    mod_pack: MinecraftModPack | None = None
    resource_pack: MinecraftResourcePack | None = None
    target_locales: list[str] = field(default_factory=list)
    source_locale: str = "en_us"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def get_all_locales(self) -> list[str]:
        """Get all available locales in this project."""
        locales = set()

        if self.mod_pack:
            locales.update(self.mod_pack.get_all_locales())

        if self.resource_pack:
            locales.update(self.resource_pack.get_locales())

        return sorted(list(locales))

    def get_total_files(self) -> int:
        """Get total number of language files in this project."""
        total = 0

        if self.mod_pack:
            total += self.mod_pack.get_total_language_files()

        if self.resource_pack:
            total += len(self.resource_pack.language_files)

        return total

    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now()
