"""
Interfaccia base per analizzatori di codice.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseAnalyzer(ABC):
    """Classe base per tutti gli analizzatori di linguaggio."""

    @abstractmethod
    def extract_file(self, filepath: str) -> dict[str, Any]:
        """Estrae nodi AST da un file.

        Returns:
            dict con: filepath, language, hash, nodes[], imports[], calls[], errors[]
        """
        ...

    @abstractmethod
    def supported_extensions(self) -> set[str]:
        """Estensioni supportate (es. {'.py', '.pyw'})."""
        ...
