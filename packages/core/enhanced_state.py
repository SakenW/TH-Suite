"""
Enhanced state management with project-specific state machines.

This module extends the basic state management with more specialized
state machines for handling complex project workflows.
"""

from enum import Enum
from typing import Dict, List, Optional, Any

from .state import SimpleStateMachine, StateMachine


class StateTransition(Enum):
    """Enhanced state transition types for project workflows."""
    
    INIT = "init"
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    COMPLETE = "complete"
    ERROR = "error"
    CANCEL = "cancel"
    VALIDATE = "validate"
    BUILD = "build"
    DEPLOY = "deploy"
    ROLLBACK = "rollback"


class ProjectStateMachine(SimpleStateMachine):
    """Enhanced state machine for project lifecycle management."""
    
    def __init__(self):
        # Define project state transitions
        valid_transitions = {
            "idle": ["initializing", "cancelled"],
            "initializing": ["scanning", "failed", "cancelled"],
            "scanning": ["processing", "failed", "cancelled", "paused"],
            "processing": ["building", "failed", "cancelled", "paused"],
            "building": ["validating", "failed", "cancelled"],
            "validating": ["completed", "failed", "processing"],  # Allow retry
            "paused": ["scanning", "processing", "cancelled"],
            "completed": ["idle", "building"],  # Allow rebuild
            "failed": ["idle", "scanning", "processing"],  # Allow retry from various states
            "cancelled": ["idle"]
        }
        super().__init__("idle", valid_transitions)
        
        # Track additional project state data
        self.progress_data: Dict[str, Any] = {}
        self.error_history: List[str] = []
        self.stage_durations: Dict[str, float] = {}
    
    def start_stage(self, stage_name: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Start a new project stage."""
        import time
        
        if not self.transition(stage_name, data):
            return False
        
        # Record stage start time
        self.set_data(f"{stage_name}_start_time", time.time())
        
        # Initialize progress for this stage
        if stage_name not in self.progress_data:
            self.progress_data[stage_name] = {
                "progress": 0.0,
                "current_step": "Starting",
                "total_steps": 1
            }
        
        return True
    
    def update_progress(self, progress: float, current_step: str = "", total_steps: int = None) -> None:
        """Update progress for the current stage."""
        stage = self.current_state
        if stage not in self.progress_data:
            self.progress_data[stage] = {}
        
        self.progress_data[stage].update({
            "progress": max(0.0, min(1.0, progress)),
            "current_step": current_step
        })
        
        if total_steps is not None:
            self.progress_data[stage]["total_steps"] = total_steps
    
    def complete_stage(self, next_stage: str = None, data: Optional[Dict[str, Any]] = None) -> bool:
        """Complete the current stage and optionally transition to next."""
        import time
        
        current_stage = self.current_state
        
        # Record completion time and duration
        start_time = self.get_data(f"{current_stage}_start_time")
        if start_time:
            duration = time.time() - start_time
            self.stage_durations[current_stage] = duration
        
        # Mark progress as complete
        if current_stage in self.progress_data:
            self.progress_data[current_stage]["progress"] = 1.0
            self.progress_data[current_stage]["current_step"] = "Completed"
        
        # Transition to next stage if specified
        if next_stage:
            return self.transition(next_stage, data)
        
        return True
    
    def record_error(self, error_message: str, error_data: Optional[Dict[str, Any]] = None) -> bool:
        """Record an error and transition to failed state."""
        self.error_history.append(error_message)
        
        error_info = {"error_message": error_message}
        if error_data:
            error_info.update(error_data)
        
        return self.transition("failed", error_info)
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of progress across all stages."""
        current_stage = self.current_state
        current_progress = self.progress_data.get(current_stage, {})
        
        return {
            "current_state": current_stage,
            "previous_state": self.previous_state,
            "current_progress": current_progress.get("progress", 0.0),
            "current_step": current_progress.get("current_step", ""),
            "stage_durations": self.stage_durations.copy(),
            "error_count": len(self.error_history),
            "last_error": self.error_history[-1] if self.error_history else None
        }
    
    def reset_project(self) -> bool:
        """Reset the project to idle state and clear all data."""
        self.progress_data.clear()
        self.error_history.clear()
        self.stage_durations.clear()
        self._data.clear()
        return self.transition("idle")


class BuildStateMachine(ProjectStateMachine):
    """Specialized state machine for build processes."""
    
    def __init__(self):
        super().__init__()
        
        # Override with build-specific transitions
        build_transitions = {
            "idle": ["preparing", "cancelled"],
            "preparing": ["compiling", "failed", "cancelled"],
            "compiling": ["linking", "failed", "cancelled", "paused"],
            "linking": ["testing", "failed", "cancelled"],
            "testing": ["packaging", "failed", "compiling"],  # Allow rebuild
            "packaging": ["deploying", "failed", "cancelled"],
            "deploying": ["completed", "failed", "cancelled"],
            "paused": ["compiling", "cancelled"],
            "completed": ["idle", "preparing"],  # Allow rebuild
            "failed": ["idle", "preparing", "compiling"],  # Allow retry
            "cancelled": ["idle"]
        }
        self._valid_transitions = build_transitions