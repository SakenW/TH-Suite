"""Client-side Patch Application Module

Lightweight patch handling for the client side.
The client only needs to:
1. Download patches from server
2. Validate patch integrity 
3. Apply patches locally
4. Report results back
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
from pathlib import Path
import json
import hashlib
from ..writeback import WritebackManager, WritebackStrategy, WritebackPlan


class PatchSource(Enum):
    """Source of the patch"""
    SERVER = "server"        # Downloaded from Trans-Hub
    LOCAL = "local"          # Local modification
    CACHED = "cached"        # From local cache
    MANUAL = "manual"        # Manual import


class PatchApplyStatus(Enum):
    """Status of patch application"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    VALIDATING = "validating"
    APPLYING = "applying"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"      # Some items succeeded


@dataclass
class ClientPatchItem:
    """Simplified patch item for client use"""
    item_id: str
    target_path: str         # Local file path
    namespace: str
    locale: str
    content: Dict[str, str]  # Translations
    expected_hash: Optional[str] = None
    
    def validate_content(self) -> bool:
        """Basic content validation"""
        if not self.content:
            return False
        
        if self.expected_hash:
            actual = hashlib.sha256(
                json.dumps(self.content, sort_keys=True).encode()
            ).hexdigest()
            return actual == self.expected_hash
        
        return True


@dataclass
class ClientPatchSet:
    """Client-side patch set"""
    patch_id: str
    name: str
    source: PatchSource
    items: List[ClientPatchItem]
    
    # Metadata from server
    server_version: Optional[str] = None
    server_signature: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # Application tracking
    status: PatchApplyStatus = PatchApplyStatus.PENDING
    applied_items: List[str] = field(default_factory=list)
    failed_items: List[str] = field(default_factory=list)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate patch set"""
        errors = []
        
        if not self.items:
            errors.append("Patch set has no items")
        
        for item in self.items:
            if not item.validate_content():
                errors.append(f"Item {item.item_id} validation failed")
        
        return len(errors) == 0, errors


@dataclass 
class PatchApplyResult:
    """Result of applying a patch"""
    patch_id: str
    success: bool
    items_total: int
    items_succeeded: int
    items_failed: int
    
    # Details
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Files modified
    modified_files: List[str] = field(default_factory=list)
    created_files: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.items_total == 0:
            return 0.0
        return self.items_succeeded / self.items_total


class ClientPatchManager:
    """Manages patch application on the client side"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path("./cache/patches")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Use the writeback manager for actual file operations
        self.writeback_manager = WritebackManager()
        
        # Track active patches
        self.active_patches: Dict[str, ClientPatchSet] = {}
        self.results: List[PatchApplyResult] = []
    
    def load_patch_from_server(self, patch_data: Dict[str, Any]) -> ClientPatchSet:
        """Load a patch downloaded from server"""
        items = []
        
        for item_data in patch_data.get('items', []):
            item = ClientPatchItem(
                item_id=item_data['id'],
                target_path=item_data['target'],
                namespace=item_data.get('namespace', 'minecraft'),
                locale=item_data.get('locale', 'zh_cn'),
                content=item_data['content'],
                expected_hash=item_data.get('hash')
            )
            items.append(item)
        
        patch = ClientPatchSet(
            patch_id=patch_data['patch_id'],
            name=patch_data.get('name', 'Unnamed Patch'),
            source=PatchSource.SERVER,
            items=items,
            server_version=patch_data.get('version'),
            server_signature=patch_data.get('signature')
        )
        
        self.active_patches[patch.patch_id] = patch
        return patch
    
    def apply_patch(self, 
                   patch_id: str, 
                   strategy: WritebackStrategy = WritebackStrategy.OVERLAY,
                   dry_run: bool = False) -> PatchApplyResult:
        """Apply a patch to local files"""
        patch = self.active_patches.get(patch_id)
        if not patch:
            raise ValueError(f"Patch {patch_id} not found")
        
        # Validate first
        valid, errors = patch.validate()
        if not valid:
            return PatchApplyResult(
                patch_id=patch_id,
                success=False,
                items_total=len(patch.items),
                items_succeeded=0,
                items_failed=len(patch.items),
                errors=errors
            )
        
        # Start applying
        patch.status = PatchApplyStatus.APPLYING
        result = PatchApplyResult(
            patch_id=patch_id,
            success=False,
            items_total=len(patch.items),
            items_succeeded=0,
            items_failed=0
        )
        
        for item in patch.items:
            try:
                if not dry_run:
                    # Create writeback plan
                    plan = self.writeback_manager.create_plan(
                        strategy=strategy,
                        target_path=Path(item.target_path),
                        content=item.content,
                        namespace=item.namespace,
                        locale=item.locale
                    )
                    
                    # Execute writeback
                    apply_result = self.writeback_manager.execute_plan(plan.plan_id)
                    
                    if apply_result.success:
                        result.items_succeeded += 1
                        patch.applied_items.append(item.item_id)
                        
                        if apply_result.target_path:
                            if apply_result.target_path.exists():
                                result.modified_files.append(str(apply_result.target_path))
                            else:
                                result.created_files.append(str(apply_result.target_path))
                    else:
                        result.items_failed += 1
                        patch.failed_items.append(item.item_id)
                        result.errors.extend(apply_result.errors)
                else:
                    # Dry run - just validate
                    result.items_succeeded += 1
                    
            except Exception as e:
                result.items_failed += 1
                patch.failed_items.append(item.item_id)
                result.errors.append(f"Item {item.item_id}: {str(e)}")
        
        # Update patch status
        if result.items_failed == 0:
            patch.status = PatchApplyStatus.SUCCESS
            result.success = True
        elif result.items_succeeded > 0:
            patch.status = PatchApplyStatus.PARTIAL
            result.success = False
        else:
            patch.status = PatchApplyStatus.FAILED
            result.success = False
        
        result.completed_at = datetime.now()
        self.results.append(result)
        
        # Cache successful patch
        if result.success:
            self._cache_patch(patch)
        
        return result
    
    def rollback_patch(self, patch_id: str) -> bool:
        """Rollback a previously applied patch"""
        # Find the apply results
        results = [r for r in self.results if r.patch_id == patch_id]
        if not results:
            return False
        
        latest_result = results[-1]
        
        # Rollback each modified file
        success = True
        for file_path in latest_result.modified_files:
            # The writeback manager handles rollback
            if not self.writeback_manager.rollback(patch_id):
                success = False
        
        return success
    
    def _cache_patch(self, patch: ClientPatchSet) -> None:
        """Cache a patch for offline use"""
        cache_file = self.cache_dir / f"{patch.patch_id}.json"
        
        data = {
            'patch_id': patch.patch_id,
            'name': patch.name,
            'source': patch.source.value,
            'server_version': patch.server_version,
            'items': [
                {
                    'id': item.item_id,
                    'target': item.target_path,
                    'namespace': item.namespace,
                    'locale': item.locale,
                    'content': item.content,
                    'hash': item.expected_hash
                }
                for item in patch.items
            ],
            'cached_at': datetime.now().isoformat()
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_cached_patch(self, patch_id: str) -> Optional[ClientPatchSet]:
        """Load a patch from cache"""
        cache_file = self.cache_dir / f"{patch_id}.json"
        
        if not cache_file.exists():
            return None
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        patch = self.load_patch_from_server(data)
        patch.source = PatchSource.CACHED
        
        return patch
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached patches"""
        import os
        
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(os.path.getsize(f) for f in cache_files)
        
        return {
            'cache_dir': str(self.cache_dir),
            'patch_count': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'patches': [f.stem for f in cache_files]
        }
    
    def clear_cache(self, older_than_days: Optional[int] = None) -> int:
        """Clear cached patches"""
        import os
        from datetime import timedelta
        
        cleared = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            if older_than_days:
                # Check age
                mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
                if datetime.now() - mtime < timedelta(days=older_than_days):
                    continue
            
            try:
                cache_file.unlink()
                cleared += 1
            except Exception:
                pass
        
        return cleared
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get patch application statistics"""
        total_patches = len(self.results)
        
        if total_patches == 0:
            return {'total_patches': 0}
        
        successful = sum(1 for r in self.results if r.success)
        failed = sum(1 for r in self.results if not r.success)
        
        total_items = sum(r.items_total for r in self.results)
        items_succeeded = sum(r.items_succeeded for r in self.results)
        
        return {
            'total_patches': total_patches,
            'successful_patches': successful,
            'failed_patches': failed,
            'success_rate': (successful / total_patches * 100) if total_patches > 0 else 0,
            'total_items': total_items,
            'items_succeeded': items_succeeded,
            'items_success_rate': (items_succeeded / total_items * 100) if total_items > 0 else 0,
            'active_patches': len(self.active_patches),
            'cache_info': self.get_cache_info()
        }
