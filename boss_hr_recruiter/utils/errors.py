"""Custom exceptions for boss-hr-recruiter skill."""


class SkillException(Exception):
    """Base exception for boss-hr-recruiter skill."""
    pass


class CookieExpiredError(SkillException):
    """Cookie已过期，需要重新登录（code 7/37）."""
    pass


class AuthRequiredError(SkillException):
    """需要重新认证."""
    pass


class RateLimitExceededError(SkillException):
    """触发平台风控，请稍后重试."""
    pass


class CDPTabRequiredError(SkillException):
    """需要CDP Chrome连接，请打开聊天页面."""
    pass


class ConfigError(SkillException):
    """配置文件错误."""
    pass


class StorageError(SkillException):
    """数据存储错误."""
    pass
