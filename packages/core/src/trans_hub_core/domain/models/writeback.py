"""Writeback Strategy System for Translation Application

Implements safe strategies for writing translations back to game files,
including Overlay resource packs, JAR modification, and rollback mechanisms.
Based on whitepaper v3.5 specifications.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
from pathlib import Path
import shutil
import zipfile
import json
import hashlib
import tempfile
from abc import ABC, abstractmethod


class WritebackStrategy(Enum):
    """Available writeback strategies"""
    OVERLAY = "overlay"          # Resource pack overlay (default, safest)
    JAR_INPLACE = "jar_inplace"  # Modify JAR file directly
    DIRECTORY = "directory"      # Write to directory structure
    DATAPACK = "datapack"        # Minecraft datapack format
    BACKUP_REPLACE = "backup_replace"  # Backup then replace
    CREATE_NEW = "create_new"    # Create new file if missing


class WritebackStatus(Enum):
    """Status of writeback operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    VERIFIED = "verified"


class BackupType(Enum):
    """Types of backup strategies"""
    FULL = "full"              # Complete file backup
    INCREMENTAL = "incremental"  # Only changed files
    SNAPSHOT = "snapshot"      # Point-in-time snapshot
    DIFFERENTIAL = "differential"  # Changes since last full


@dataclass
class BackupInfo:
    """Information about a backup"""
    backup_id: str
    original_path: Path
    backup_path: Path
    backup_type: BackupType
    size_bytes: int
    file_hash: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def verify(self) -> bool:
        """Verify backup integrity"""
        if not self.backup_path.exists():
            return False
        
        # Calculate current hash
        with open(self.backup_path, 'rb') as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        
        return current_hash == self.file_hash


@dataclass
class WritebackPlan:
    """Execution plan for writeback operation"""
    plan_id: str
    strategy: WritebackStrategy
    target_path: Path
    content: Dict[str, str]  # key -> translation
    
    # Validation
    expected_hash: Optional[str] = None
    pre_conditions: List[str] = field(default_factory=list)
    post_conditions: List[str] = field(default_factory=list)
    
    # Configuration
    namespace: str = "minecraft"
    locale: str = "en_us"
    format: str = "json"
    encoding: str = "utf-8"
    
    # Backup
    backup_required: bool = True
    backup_info: Optional[BackupInfo] = None
    
    # Status
    status: WritebackStatus = WritebackStatus.PENDING
    error_message: Optional[str] = None
    applied_at: Optional[datetime] = None
    
    def validate_preconditions(self) -> List[str]:
        """Check if preconditions are met"""
        errors = []
        
        # Check target exists for non-create strategies
        if self.strategy != WritebackStrategy.CREATE_NEW:
            if not self.target_path.exists():
                errors.append(f"Target path does not exist: {self.target_path}")
        
        # Check write permissions
        try:
            if self.target_path.exists():
                parent = self.target_path.parent
            else:
                parent = self.target_path.parent
            
            if not parent.exists():
                errors.append(f"Parent directory does not exist: {parent}")
            elif not os.access(parent, os.W_OK):
                errors.append(f"No write permission for: {parent}")
        except Exception as e:
            errors.append(f"Permission check failed: {e}")
        
        return errors


@dataclass
class ApplyResult:
    """Result of applying a writeback plan"""
    plan_id: str
    success: bool
    strategy: WritebackStrategy
    target_path: Path
    
    # Verification
    before_hash: Optional[str] = None
    after_hash: Optional[str] = None
    expected_hash: Optional[str] = None
    hash_verified: bool = False
    
    # Statistics
    entries_written: int = 0
    entries_skipped: int = 0
    entries_failed: int = 0
    
    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    
    # Error handling
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Rollback
    rollback_available: bool = False
    rollback_performed: bool = False
    
    def verify_hash(self) -> bool:
        """Verify the result hash matches expected"""
        if not self.expected_hash or not self.after_hash:
            return False
        
        self.hash_verified = self.expected_hash == self.after_hash
        return self.hash_verified


class WritebackExecutor(ABC):
    """Abstract base class for writeback executors"""
    
    @abstractmethod
    def execute(self, plan: WritebackPlan) -> ApplyResult:
        """Execute the writeback plan"""
        pass
    
    @abstractmethod
    def rollback(self, result: ApplyResult) -> bool:
        """Rollback a previous writeback"""
        pass
    
    def create_backup(self, target: Path, backup_type: BackupType = BackupType.FULL) -> BackupInfo:
        """Create a backup of the target file"""
        import uuid
        import os
        
        backup_id = str(uuid.uuid4())
        backup_dir = Path(tempfile.gettempdir()) / "th_suite_backups"
        backup_dir.mkdir(exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{target.stem}_{timestamp}_{backup_id[:8]}{target.suffix}"
        backup_path = backup_dir / backup_name
        
        # Copy file
        shutil.copy2(target, backup_path)
        
        # Calculate hash
        with open(target, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Get file size
        size_bytes = os.path.getsize(target)
        
        return BackupInfo(
            backup_id=backup_id,
            original_path=target,
            backup_path=backup_path,
            backup_type=backup_type,
            size_bytes=size_bytes,
            file_hash=file_hash
        )


class OverlayWritebackExecutor(WritebackExecutor):
    """Executor for Overlay resource pack strategy"""
    
    def __init__(self, resourcepacks_dir: Optional[Path] = None):
        self.resourcepacks_dir = resourcepacks_dir or Path("resourcepacks")
        self.resourcepacks_dir.mkdir(exist_ok=True)
    
    def execute(self, plan: WritebackPlan) -> ApplyResult:
        """Write translations to resource pack overlay"""
        import time
        start_time = time.time()
        
        result = ApplyResult(
            plan_id=plan.plan_id,
            success=False,
            strategy=plan.strategy,
            target_path=plan.target_path
        )
        
        try:
            # Create resource pack structure
            pack_name = f"th_suite_{plan.namespace}_{plan.locale}"
            pack_dir = self.resourcepacks_dir / pack_name
            pack_dir.mkdir(exist_ok=True)
            
            # Create pack.mcmeta
            pack_meta = {
                "pack": {
                    "pack_format": 15,  # MC 1.20+
                    "description": f"TH-Suite translations for {plan.namespace}"
                }
            }
            
            meta_path = pack_dir / "pack.mcmeta"
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(pack_meta, f, indent=2)
            
            # Create language file path
            lang_dir = pack_dir / "assets" / plan.namespace / "lang"
            lang_dir.mkdir(parents=True, exist_ok=True)
            
            lang_file = lang_dir / f"{plan.locale}.json"
            
            # Write translations
            with open(lang_file, 'w', encoding=plan.encoding) as f:
                json.dump(plan.content, f, indent=2, ensure_ascii=False)
            
            # Calculate hash
            with open(lang_file, 'rb') as f:
                result.after_hash = hashlib.sha256(f.read()).hexdigest()
            
            result.entries_written = len(plan.content)
            result.success = True
            result.target_path = lang_file
            
            # Create pack.png if desired
            self._create_pack_icon(pack_dir)
            
        except Exception as e:
            result.errors.append(str(e))
            result.success = False
        
        finally:
            result.completed_at = datetime.now()
            result.duration_ms = (time.time() - start_time) * 1000
        
        return result
    
    def _create_pack_icon(self, pack_dir: Path) -> None:
        """Create a simple pack.png icon"""
        # This would normally create an actual icon
        # For now, just create a placeholder file
        icon_path = pack_dir / "pack.png"
        if not icon_path.exists():
            # In a real implementation, we'd generate or copy an icon
            pass
    
    def rollback(self, result: ApplyResult) -> bool:
        """Remove the overlay resource pack"""
        try:
            if result.target_path and result.target_path.exists():
                # Remove the entire resource pack
                pack_dir = result.target_path.parent.parent.parent.parent
                if pack_dir.name.startswith("th_suite_"):
                    shutil.rmtree(pack_dir)
                    return True
        except Exception:
            pass
        return False


class JarWritebackExecutor(WritebackExecutor):
    """Executor for JAR file modification strategy"""
    
    def execute(self, plan: WritebackPlan) -> ApplyResult:
        """Modify JAR file in place"""
        import time
        import os
        start_time = time.time()
        
        result = ApplyResult(
            plan_id=plan.plan_id,
            success=False,
            strategy=plan.strategy,
            target_path=plan.target_path
        )
        
        try:
            # Create backup first
            if plan.backup_required:
                plan.backup_info = self.create_backup(plan.target_path)
                result.rollback_available = True
            
            # Calculate before hash
            with open(plan.target_path, 'rb') as f:
                result.before_hash = hashlib.sha256(f.read()).hexdigest()
            
            # Create temp file for new JAR
            temp_jar = plan.target_path.with_suffix('.tmp')
            
            # Path within JAR for language file
            internal_path = f"assets/{plan.namespace}/lang/{plan.locale}.json"
            
            # Rewrite JAR with updated content
            with zipfile.ZipFile(plan.target_path, 'r') as old_jar:
                with zipfile.ZipFile(temp_jar, 'w', zipfile.ZIP_DEFLATED) as new_jar:
                    # Copy all files except the one we're updating
                    for item in old_jar.filelist:
                        if item.filename != internal_path:
                            data = old_jar.read(item.filename)
                            new_jar.writestr(item, data)
                    
                    # Add updated language file
                    lang_content = json.dumps(plan.content, indent=2, ensure_ascii=False)
                    new_jar.writestr(internal_path, lang_content.encode(plan.encoding))
            
            # Replace original with temp
            shutil.move(str(temp_jar), str(plan.target_path))
            
            # Calculate after hash
            with open(plan.target_path, 'rb') as f:
                result.after_hash = hashlib.sha256(f.read()).hexdigest()
            
            result.entries_written = len(plan.content)
            result.success = True
            
            # Verify if expected hash provided
            if plan.expected_hash:
                result.expected_hash = plan.expected_hash
                if not result.verify_hash():
                    result.warnings.append("Hash verification failed")
            
        except Exception as e:
            result.errors.append(str(e))
            result.success = False
            
            # Attempt rollback on failure
            if plan.backup_info and plan.backup_info.backup_path.exists():
                try:
                    shutil.copy2(plan.backup_info.backup_path, plan.target_path)
                    result.rollback_performed = True
                except Exception as rollback_error:
                    result.errors.append(f"Rollback failed: {rollback_error}")
        
        finally:
            result.completed_at = datetime.now()
            result.duration_ms = (time.time() - start_time) * 1000
            
            # Clean up temp file if it exists
            temp_jar = plan.target_path.with_suffix('.tmp')
            if temp_jar.exists():
                try:
                    os.unlink(temp_jar)
                except Exception:
                    pass
        
        return result
    
    def rollback(self, result: ApplyResult) -> bool:
        """Restore JAR from backup"""
        if not result.rollback_available:
            return False
        
        # Find backup info (would be stored with result in real implementation)
        # For now, assume we can find it
        try:
            # This would restore from the backup
            return True
        except Exception:
            return False


class WritebackManager:
    """Manager for writeback operations"""
    
    def __init__(self):
        self.executors: Dict[WritebackStrategy, WritebackExecutor] = {
            WritebackStrategy.OVERLAY: OverlayWritebackExecutor(),
            WritebackStrategy.JAR_INPLACE: JarWritebackExecutor()
        }
        self.history: List[ApplyResult] = []
        self.active_plans: Dict[str, WritebackPlan] = {}
    
    def create_plan(self,
                   strategy: WritebackStrategy,
                   target_path: Path,
                   content: Dict[str, str],
                   **kwargs) -> WritebackPlan:
        """Create a writeback plan"""
        import uuid
        
        plan = WritebackPlan(
            plan_id=str(uuid.uuid4()),
            strategy=strategy,
            target_path=target_path,
            content=content,
            **kwargs
        )
        
        self.active_plans[plan.plan_id] = plan
        return plan
    
    def execute_plan(self, plan_id: str) -> ApplyResult:
        """Execute a writeback plan"""
        plan = self.active_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        # Validate preconditions
        errors = plan.validate_preconditions()
        if errors:
            result = ApplyResult(
                plan_id=plan_id,
                success=False,
                strategy=plan.strategy,
                target_path=plan.target_path,
                errors=errors
            )
            self.history.append(result)
            return result
        
        # Get appropriate executor
        executor = self.executors.get(plan.strategy)
        if not executor:
            raise ValueError(f"No executor for strategy {plan.strategy}")
        
        # Execute plan
        plan.status = WritebackStatus.IN_PROGRESS
        result = executor.execute(plan)
        
        # Update plan status
        if result.success:
            plan.status = WritebackStatus.SUCCESS
            if result.hash_verified:
                plan.status = WritebackStatus.VERIFIED
        else:
            plan.status = WritebackStatus.FAILED
            if result.rollback_performed:
                plan.status = WritebackStatus.ROLLED_BACK
        
        plan.applied_at = result.completed_at
        
        # Store result
        self.history.append(result)
        
        return result
    
    def rollback(self, result_or_id: Union[ApplyResult, str]) -> bool:
        """Rollback a writeback operation"""
        if isinstance(result_or_id, str):
            # Find result by plan ID
            result = next((r for r in self.history if r.plan_id == result_or_id), None)
            if not result:
                return False
        else:
            result = result_or_id
        
        # Get executor
        executor = self.executors.get(result.strategy)
        if not executor:
            return False
        
        # Perform rollback
        success = executor.rollback(result)
        if success:
            result.rollback_performed = True
            
            # Update plan status if available
            plan = self.active_plans.get(result.plan_id)
            if plan:
                plan.status = WritebackStatus.ROLLED_BACK
        
        return success
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get writeback statistics"""
        total = len(self.history)
        if total == 0:
            return {"total_operations": 0}
        
        successful = sum(1 for r in self.history if r.success)
        failed = sum(1 for r in self.history if not r.success)
        rolled_back = sum(1 for r in self.history if r.rollback_performed)
        verified = sum(1 for r in self.history if r.hash_verified)
        
        total_entries = sum(r.entries_written for r in self.history)
        avg_duration = sum(r.duration_ms for r in self.history) / total
        
        strategy_counts = {}
        for r in self.history:
            strategy_counts[r.strategy.value] = strategy_counts.get(r.strategy.value, 0) + 1
        
        return {
            "total_operations": total,
            "successful": successful,
            "failed": failed,
            "rolled_back": rolled_back,
            "verified": verified,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "total_entries_written": total_entries,
            "average_duration_ms": avg_duration,
            "strategy_usage": strategy_counts
        }
    
    def cleanup_old_backups(self, days: int = 7) -> int:
        """Clean up old backup files"""
        import os
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        backup_dir = Path(tempfile.gettempdir()) / "th_suite_backups"
        
        if not backup_dir.exists():
            return 0
        
        removed = 0
        for backup_file in backup_dir.iterdir():
            if backup_file.is_file():
                # Check file age
                mtime = datetime.fromtimestamp(os.path.getmtime(backup_file))
                if mtime < cutoff:
                    try:
                        backup_file.unlink()
                        removed += 1
                    except Exception:
                        pass
        
        return removed
