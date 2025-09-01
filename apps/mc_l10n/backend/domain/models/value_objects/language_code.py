"""语言代码值对象"""

from packages.core.data.models import ValueObject


class LanguageCode(ValueObject):
    """语言代码值对象"""

    # 支持的语言代码映射
    SUPPORTED_LANGUAGES = {
        "en_us": "English (US)",
        "zh_cn": "简体中文",
        "zh_tw": "繁體中文",
        "ja_jp": "日本語",
        "ko_kr": "한국어",
        "fr_fr": "Français",
        "de_de": "Deutsch",
        "es_es": "Español",
        "ru_ru": "Русский",
        "pt_br": "Português (Brasil)",
        "it_it": "Italiano",
        "nl_nl": "Nederlands",
    }

    def __init__(self, code: str):
        normalized_code = code.lower().replace("-", "_")
        if normalized_code not in self.SUPPORTED_LANGUAGES:
            # 允许未知语言代码，但发出警告
            import warnings

            warnings.warn(f"不支持的语言代码: {code}，将作为自定义语言处理")
        self._code = normalized_code

    @property
    def code(self) -> str:
        return self._code

    @property
    def display_name(self) -> str:
        return self.SUPPORTED_LANGUAGES.get(self._code, f"Unknown ({self._code})")

    def is_chinese(self) -> bool:
        return self._code in ["zh_cn", "zh_tw"]

    def is_english(self) -> bool:
        return self._code == "en_us"

    def __str__(self) -> str:
        return self._code

    def __eq__(self, other) -> bool:
        if not isinstance(other, LanguageCode):
            return False
        return self._code == other._code

    def __hash__(self) -> int:
        return hash(self._code)
