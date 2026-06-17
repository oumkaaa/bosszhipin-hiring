"""Authentication management for boss-hr-recruiter skill."""

from pathlib import Path
from boss_agent_cli.auth.manager import AuthManager as BACAuthManager
from .errors import CookieExpiredError, AuthRequiredError


class AuthManager:
    """包装 boss-agent-cli 的 AuthManager."""

    def __init__(self, data_dir: str = None):
        """初始化认证管理器.

        Args:
            data_dir: boss-agent-cli数据目录，默认使用~/.boss-agent
        """
        if data_dir is None:
            data_dir = str(Path.home() / '.boss-agent')

        self.data_dir = Path(data_dir)
        self.auth = BACAuthManager(self.data_dir)

    def check_login_status(self) -> bool:
        """检查是否已登录."""
        try:
            # 尝试读取认证状态
            token_file = self.data_dir / 'tokens.json'
            if not token_file.exists():
                return False

            # TODO: 实现真正的登录状态检查
            return True
        except Exception:
            return False

    def handle_cookie_expired(self) -> None:
        """处理Cookie过期，抛出异常让外部处理."""
        raise CookieExpiredError(
            "Cookie已过期，请在Chrome中重新登录"
            "（在项目根目录运行：boss login）"
        )

    def handle_auth_required(self) -> None:
        """处理需要认证的情况."""
        raise AuthRequiredError(
            "需要重新认证。请运行：boss login"
        )
