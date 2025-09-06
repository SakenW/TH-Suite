"""
领域服务
包含不属于任何单一实体的业务逻辑
"""

from .translation_service import TranslationService
from .validation_service import ValidationService
from .conflict_resolution_service import (
    ConflictResolutionService,
    ConflictResolutionStrategy,
    TranslationConflict
)
from .terminology_service import (
    TerminologyService,
    Term,
    Glossary
)

__all__ = [
    'TranslationService',
    'ValidationService',
    'ConflictResolutionService',
    'ConflictResolutionStrategy',
    'TranslationConflict',
    'TerminologyService',
    'Term',
    'Glossary',
]