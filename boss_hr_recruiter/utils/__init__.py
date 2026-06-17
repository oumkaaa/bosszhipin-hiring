"""Utilities for boss-hr-recruiter skill."""

from .errors import (
    SkillException,
    CookieExpiredError,
    AuthRequiredError,
    RateLimitExceededError,
    CDPTabRequiredError,
    ConfigError,
    StorageError,
)
from .config import load_config, load_candidates, save_candidates
from .logger import SkillLogger
from .auth import AuthManager
from .storage import CandidateStorage

__all__ = [
    'SkillException',
    'CookieExpiredError',
    'AuthRequiredError',
    'RateLimitExceededError',
    'CDPTabRequiredError',
    'ConfigError',
    'StorageError',
    'load_config',
    'load_candidates',
    'save_candidates',
    'SkillLogger',
    'AuthManager',
    'CandidateStorage',
]
