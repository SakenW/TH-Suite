"""
Application state management utilities.

This module provides basic state management functionality for
maintaining application state across different components.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class StateTransition(Enum):
    """Common state transition types."""

    INIT = "init"
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    COMPLETE = "complete"
    ERROR = "error"
    CANCEL = "cancel"


class StateMachine(ABC):
    """Abstract base class for state machines."""

    def __init__(self, initial_state: str = "idle"):
        self._current_state = initial_state
        self._previous_state: str | None = None
        self._data: dict[str, Any] = {}

    @property
    def current_state(self) -> str:
        """Get the current state."""
        return self._current_state

    @property
    def previous_state(self) -> str | None:
        """Get the previous state."""
        return self._previous_state

    def set_data(self, key: str, value: Any) -> None:
        """Set state data."""
        self._data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get state data."""
        return self._data.get(key, default)

    @abstractmethod
    def transition(self, new_state: str, data: dict[str, Any] | None = None) -> bool:
        """Transition to a new state."""
        pass

    @abstractmethod
    def is_valid_transition(self, from_state: str, to_state: str) -> bool:
        """Check if a state transition is valid."""
        pass


class SimpleStateMachine(StateMachine):
    """Simple implementation of a state machine."""

    def __init__(
        self,
        initial_state: str = "idle",
        valid_transitions: dict[str, list[str]] | None = None,
    ):
        super().__init__(initial_state)
        self._valid_transitions = valid_transitions or {}

    def transition(self, new_state: str, data: dict[str, Any] | None = None) -> bool:
        """Transition to a new state."""
        if not self.is_valid_transition(self._current_state, new_state):
            return False

        self._previous_state = self._current_state
        self._current_state = new_state

        if data:
            self._data.update(data)

        return True

    def is_valid_transition(self, from_state: str, to_state: str) -> bool:
        """Check if a state transition is valid."""
        if not self._valid_transitions:
            return True  # Allow all transitions if no restrictions defined

        valid_targets = self._valid_transitions.get(from_state, [])
        return to_state in valid_targets

    def add_valid_transition(self, from_state: str, to_state: str) -> None:
        """Add a valid state transition."""
        if from_state not in self._valid_transitions:
            self._valid_transitions[from_state] = []

        if to_state not in self._valid_transitions[from_state]:
            self._valid_transitions[from_state].append(to_state)


class JobStateMachine(SimpleStateMachine):
    """State machine for managing job states."""

    def __init__(self) -> None:
        # Define common job state transitions
        valid_transitions = {
            "idle": ["pending", "cancelled"],
            "pending": ["in_progress", "cancelled"],
            "in_progress": ["completed", "failed", "cancelled", "paused"],
            "paused": ["in_progress", "cancelled"],
            "completed": ["idle"],
            "failed": ["idle", "pending"],  # Allow retry
            "cancelled": ["idle"],
        }
        super().__init__("idle", valid_transitions)


class State:
    """Simple state container for holding application state."""

    def __init__(self, data: dict[str, Any] | None = None):
        self._data: dict[str, Any] = data or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the state."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the state."""
        self._data[key] = value

    def update(self, data: dict[str, Any]) -> None:
        """Update the state with new data."""
        self._data.update(data)

    def clear(self) -> None:
        """Clear all state data."""
        self._data.clear()

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary."""
        return self._data.copy()

    def __contains__(self, key: str) -> bool:
        """Check if key exists in state."""
        return key in self._data

    def __len__(self) -> int:
        """Get number of items in state."""
        return len(self._data)
