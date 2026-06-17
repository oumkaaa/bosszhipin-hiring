"""Unified adapter for boss-agent-cli SDK calls.

Central interface for all platform interactions, handling auth checks,
error logging, and result recording.
"""

from typing import Any, Dict, List, Optional
from boss_agent_cli.auth.manager import AuthManager as BACAuthManager
from boss_agent_cli.api.recruiter_client import BossRecruiterClient

from ..utils.logger import SkillLogger
from ..utils.errors import CookieExpiredError


class AgentCliAdapter:
    """Unified boss-agent-cli interface for orchestration layer."""

    def __init__(self, auth: BACAuthManager, logger: SkillLogger):
        self.auth = auth
        self.logger = logger
        self.client = BossRecruiterClient(auth)

    # ===== Read Operations =====

    def list_new_chats(
        self,
        job_id: str,
        page: int = 1,
        label_id: int = 1
    ) -> Dict[str, Any]:
        """Fetch new greeting candidates (chat list).

        Args:
            job_id: Job ID
            page: Page number (default 1)
            label_id: Label filter (1=new, etc)

        Returns:
            API response dict with friendList
        """
        try:
            result = self.client.friend_list(
                page=page,
                label_id=label_id,
                job_id=job_id
            )
            self._check_result(result, "friend_list")
            return result
        except Exception as e:
            self.logger.error(f"Failed to list new chats: {e}")
            raise

    def list_recommend_candidates(
        self,
        job_id: str,
        page: int = 1
    ) -> Dict[str, Any]:
        """Fetch recommended candidates.

        Args:
            job_id: Job ID
            page: Page number

        Returns:
            API response dict with geeks list
        """
        try:
            result = self.client.greet_rec_list(page=page, job_id=job_id)
            self._check_result(result, "greet_rec_list")
            return result
        except Exception as e:
            self.logger.error(f"Failed to list recommend candidates: {e}")
            raise

    def get_friend_detail(self, friend_ids: List[int]) -> Dict[str, Any]:
        """Get friend details (includes encryptUid, encryptJobId).

        Args:
            friend_ids: List of friend IDs

        Returns:
            API response with friendList
        """
        try:
            result = self.client.friend_detail(friend_ids)
            self._check_result(result, "friend_detail")
            return result
        except Exception as e:
            self.logger.error(f"Failed to get friend detail: {e}")
            raise

    def get_resume(
        self,
        geek_id: str,
        job_id: str,
        security_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get full resume data.

        Args:
            geek_id: Geek ID (encryptGeekId)
            job_id: Job ID (encryptJobId)
            security_id: Optional security ID

        Returns:
            API response with resume data
        """
        try:
            result = self.client.view_geek(geek_id, job_id)
            self._check_result(result, "view_geek")
            return result
        except Exception as e:
            self.logger.error(f"Failed to get resume for {geek_id}: {e}")
            raise

    def get_latest_messages(
        self,
        friend_ids: List[int],
        count: int = 20
    ) -> Dict[str, Any]:
        """Get latest chat messages from friends.

        Args:
            friend_ids: List of friend IDs
            count: Number of messages to fetch

        Returns:
            API response with chat messages
        """
        try:
            result = self.client.last_messages(friend_ids)
            self._check_result(result, "last_messages")
            return result
        except Exception as e:
            self.logger.error(f"Failed to get messages: {e}")
            raise

    # ===== Write Operations =====

    def send_message(
        self,
        friend_id: int,
        content: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Send message to candidate.

        Args:
            friend_id: Recipient friend ID
            content: Message content
            dry_run: If True, simulate only (no real send)

        Returns:
            API result dict with code/message
        """
        if dry_run:
            self.logger.info(f"[DRY-RUN] Would send to {friend_id}: {content[:50]}...")
            return {"code": 0, "message": "dry_run", "dry_run": True}

        try:
            self.logger.info(f"Sending message to {friend_id}")
            result = self.client.send_message_by_friend(friend_id, content)
            self._check_result(result, "send_message_by_friend")
            return result
        except Exception as e:
            self.logger.error(f"Failed to send message to {friend_id}: {e}")
            raise

    def request_resume(
        self,
        friend_id: int,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Request candidate to share resume.

        Args:
            friend_id: Recipient friend ID
            dry_run: If True, simulate only

        Returns:
            API result dict
        """
        if dry_run:
            self.logger.info(f"[DRY-RUN] Would request resume from {friend_id}")
            return {"code": 0, "message": "dry_run", "dry_run": True}

        try:
            self.logger.info(f"Requesting resume from {friend_id}")
            result = self.client.exchange_request_by_friend(
                friend_id,
                exchange_type=4  # Resume exchange type
            )
            self._check_result(result, "exchange_request_by_friend")
            return result
        except Exception as e:
            self.logger.error(f"Failed to request resume from {friend_id}: {e}")
            raise

    # ===== Auth Check =====

    def check_auth_status(self) -> Dict[str, Any]:
        """Check current authentication status.

        Returns:
            Status dict with auth state
        """
        try:
            result = self.client.status_live()
            return result
        except Exception as e:
            self.logger.error(f"Failed to check auth status: {e}")
            return {"code": -1, "message": str(e)}

    # ===== Cleanup =====

    def close(self):
        """Close client connection."""
        self.client.close()

    # ===== Internal =====

    def _check_result(self, result: Dict[str, Any], method: str):
        """Check API result and handle errors.

        Args:
            result: API response dict
            method: Method name for logging

        Raises:
            CookieExpiredError: If cookie/auth expired
            Exception: For other errors
        """
        code = result.get("code", -1)

        # Check for cookie expiry
        if code in (7, 37):
            self.logger.critical(f"Cookie expired (code {code})")
            raise CookieExpiredError(f"{method} failed: cookie expired")

        # Check for general failure
        if code != 0:
            msg = result.get("message", "Unknown error")
            self.logger.error(f"{method} returned code {code}: {msg}")
            raise Exception(f"{method} failed: {msg}")
