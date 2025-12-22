"""TransHub Tools parsers package.

Provides parsers for various game localization file formats.
"""

from .base import BaseParser, ParseResult
from .cfg_parser import CfgParser
from .factory import (
    ParserFactory,
    can_parse_file,
    clear_parser_cache,
    get_parser_for_file,
    get_parser_info,
    get_supported_extensions,
    register_parser,
)
from .json_parser import JsonParser
from .lang_parser import LangParser
from .toml_parser import TomlParser

__all__ = [
    "BaseParser",
    "ParseResult",
    "JsonParser",
    "LangParser",
    "TomlParser",
    "CfgParser",
    "ParserFactory",
    "get_parser_for_file",
    "register_parser",
    "get_supported_extensions",
    "can_parse_file",
    "get_parser_info",
    "clear_parser_cache",
]
