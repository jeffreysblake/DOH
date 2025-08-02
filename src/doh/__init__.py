"""
DOH - Directory Oh-no, Handle this!
A smart auto-commit monitoring system for git repositories.
"""

__version__ = "2.0.0"
__author__ = "DOH Project"
__email__ = "doh@example.com"

from .core import DohCore
from .config import DohConfig  
from .git_stats import GitStats

__all__ = ["DohCore", "DohConfig", "GitStats"]
