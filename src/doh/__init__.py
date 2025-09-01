"""
DOH - Delta-Oriented Historykeeper
A smart auto-commit monitoring system for git repositories.
"""

__version__ = "2.0.0"
__author__ = "Jeff Blake"
__email__ = "jeffrey.s.blake@gmail.com"

from .core import DohCore
from .config import DohConfig
from .git_stats import GitStats

__all__ = ["DohCore", "DohConfig", "GitStats"]
