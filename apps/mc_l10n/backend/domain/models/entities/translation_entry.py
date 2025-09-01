"""
翻译条目实体

翻译条目的领域实体表示
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.models.enums import TranslationStatus
from domain.models.value_objects.translation_key import TranslationKey


@dataclass
class TranslationEntry:
    """翻译条目实体"""
    
    entry_id: str
    translation_key: TranslationKey
    source_value: str
    translated_value: Optional[str] = None
    status: TranslationStatus = TranslationStatus.UNTRANSLATED
    comment: Optional[str] = None
    context: Optional[str] = None
    created_at: datetime = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()