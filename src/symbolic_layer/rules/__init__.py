"""
Tajwīd Rule Classes.

This package contains the base rule class for Tajwīd rule implementations.
The actual rules are loaded declaratively from YAML configuration files.
"""

from .base_rule import BaseRule

__all__ = [
    "BaseRule",
]
