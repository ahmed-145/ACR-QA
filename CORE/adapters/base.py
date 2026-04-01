#!/usr/bin/env python3
"""
ACR-QA Language Adapter Base Class
Abstract base for language-specific tool orchestration.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class LanguageAdapter(ABC):
    """
    Abstract base class for language-specific analysis adapters.

    Each language adapter defines:
    - Which tools to run (e.g., Ruff for Python, ESLint for JS)
    - How to invoke those tools
    - What file extensions to scan
    - Language-specific rule mappings

    Usage:
        adapter = PythonAdapter(target_dir="/path/to/project")
        results = adapter.run_tools()
        mappings = adapter.get_rule_mappings()
    """

    def __init__(self, target_dir: str = "."):
        self.target_dir = Path(target_dir)

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Human-readable language name (e.g., 'Python', 'JavaScript')."""
        ...

    @property
    @abstractmethod
    def file_extensions(self) -> list[str]:
        """File extensions this adapter handles (e.g., ['.py'], ['.js', '.ts'])."""
        ...

    @abstractmethod
    def get_tools(self) -> list[dict[str, Any]]:
        """
        Return list of tools this adapter uses.

        Returns:
            List of dicts: [{"name": "ruff", "version": "0.x", "purpose": "..."}]
        """
        ...

    @abstractmethod
    def run_tools(self, output_dir: str = "DATA/outputs") -> dict[str, Any]:
        """
        Run all language-specific analysis tools.

        Args:
            output_dir: Directory to write tool output files

        Returns:
            Dict with tool results and any errors
        """
        ...

    @abstractmethod
    def get_rule_mappings(self) -> dict[str, str]:
        """
        Return tool-specific rule ID → canonical rule ID mappings.

        Returns:
            Dict mapping tool rule IDs to canonical IDs
        """
        ...

    def find_files(self) -> list[Path]:
        """Find all files matching this adapter's extensions in target_dir."""
        files: list[Path] = []
        for ext in self.file_extensions:
            files.extend(self.target_dir.rglob(f"*{ext}"))
        return sorted(files)

    def supports_file(self, filepath: str) -> bool:
        """Check if this adapter handles the given file."""
        return Path(filepath).suffix in self.file_extensions
