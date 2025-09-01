"""
Database utilities and interfaces for the core package.

This module provides basic database-related functionality that can be
shared across different applications.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional


class DatabaseConnection(ABC):
    """Abstract base class for database connections."""
    
    @abstractmethod
    async def execute(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a query with optional parameters."""
        pass
    
    @abstractmethod
    async def fetch_one(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Fetch a single row from the database."""
        pass
    
    @abstractmethod
    async def fetch_all(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fetch all rows from the database."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the database connection."""
        pass


class DatabaseManager(ABC):
    """Abstract base class for database managers."""
    
    @abstractmethod
    async def get_connection(self) -> DatabaseConnection:
        """Get a database connection."""
        pass
    
    @abstractmethod
    async def close_all_connections(self) -> None:
        """Close all database connections."""
        pass


class SimpleInMemoryConnection(DatabaseConnection):
    """Simple in-memory database connection for testing."""
    
    def __init__(self):
        self._data: Dict[str, List[Dict[str, Any]]] = {}
    
    async def execute(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a query (mock implementation)."""
        return True
    
    async def fetch_one(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Fetch a single row (mock implementation)."""
        return None
    
    async def fetch_all(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fetch all rows (mock implementation)."""
        return []
    
    async def close(self) -> None:
        """Close the connection."""
        pass


class SQLCipherDatabase:
    """SQLCipher database wrapper for encrypted storage."""
    
    def __init__(self, db_path: str, password: str = None):
        self.db_path = db_path
        self.password = password
        self._connection = None
    
    def _get_connection(self):
        """Get database connection (mock implementation)."""
        if self._connection is None:
            # In a real implementation, this would create an SQLCipher connection
            self._connection = SimpleInMemoryConnection()
        return self._connection
    
    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def execute(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a query."""
        conn = self._get_connection()
        return await conn.execute(query, parameters)
    
    async def fetch_one(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Fetch a single row."""
        conn = self._get_connection()
        return await conn.fetch_one(query, parameters)
    
    async def fetch_all(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fetch all rows."""
        conn = self._get_connection()
        return await conn.fetch_all(query, parameters)