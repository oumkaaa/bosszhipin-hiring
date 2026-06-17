"""Data persistence for boss-hr-recruiter skill."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .errors import StorageError
from .config import load_candidates, save_candidates


class CandidateStorage:
    """管理候选人数据的存取."""

    def __init__(self, runtime_dir: str):
        """初始化存储器.

        Args:
            runtime_dir: 运行时目录
        """
        self.runtime_dir = Path(runtime_dir)
        self.candidates_file = self.runtime_dir / "candidates.json"

    def load(self) -> List[Dict[str, Any]]:
        """加载候选人列表."""
        try:
            return load_candidates(str(self.runtime_dir))
        except Exception as e:
            raise StorageError(f"加载候选人列表失败: {e}")

    def save(self, candidates: List[Dict[str, Any]]) -> None:
        """保存候选人列表（原子写入）."""
        try:
            save_candidates(str(self.runtime_dir), candidates)
        except Exception as e:
            raise StorageError(f"保存候选人列表失败: {e}")

    def transition(
        self,
        candidate: Dict[str, Any],
        to_status: str,
        **fields
    ) -> None:
        """State transition for single candidate.

        Args:
            candidate: Candidate data dict
            to_status: Target status
            **fields: Extra fields (e.g. exclude_reason)
        """
        # Get old status BEFORE updating
        old_status = candidate.get('status', 'NEW')

        # Update status
        candidate['status'] = to_status

        # Map state transition to action
        action_map = {
            ('NEW', '首轮沟通'): 'first_message_sent',
            ('NEW', 'FAILED'): 'screened_failed',
            ('首轮沟通', '首轮沟通追加提问'): 'follow_up_sent',
            ('首轮沟通', '二轮沟通'): 'reply_qualified',
            ('首轮沟通', 'FAILED'): 'reply_failed',
            ('首轮沟通追加提问', '二轮沟通'): 'followup_reply_qualified',
            ('首轮沟通追加提问', 'FAILED'): 'followup_reply_failed',
            ('二轮沟通', '等待简历'): 'resume_requested',
            ('二轮沟通', '简历已获取'): 'resume_confirmed',
            ('二轮沟通', 'FAILED'): 'second_round_failed',
            ('等待简历', '简历已获取'): 'resume_confirmed',
            ('等待简历', 'FAILED'): 'resume_wait_failed',
        }

        for (from_st, to_st), action in action_map.items():
            if old_status == from_st and to_status == to_st:
                candidate['last_action'] = action
                break

        # Update other fields
        candidate.update(fields)

        # Add timestamp if new candidate
        if 'created_at' not in candidate:
            candidate['created_at'] = datetime.now().isoformat()

    def add_candidate(self, candidate: Dict[str, Any]) -> None:
        """添加新候选人."""
        candidates = self.load()

        # 检查是否已存在
        if any(c['uid'] == candidate['uid'] for c in candidates):
            return

        # 添加创建时间和初始状态
        if 'created_at' not in candidate:
            candidate['created_at'] = datetime.now().isoformat()
        if 'status' not in candidate:
            candidate['status'] = 'NEW'

        candidates.append(candidate)
        self.save(candidates)

    def get_candidate(self, uid: str) -> Dict[str, Any] | None:
        """获取单个候选人."""
        candidates = self.load()
        for c in candidates:
            if c['uid'] == uid:
                return c
        return None

    def update_candidate(self, uid: str, **updates) -> None:
        """更新单个候选人信息."""
        candidates = self.load()
        for c in candidates:
            if c['uid'] == uid:
                c.update(updates)
                break
        self.save(candidates)

    def get_by_status(self, status: str) -> List[Dict[str, Any]]:
        """获取特定状态的候选人."""
        candidates = self.load()
        return [c for c in candidates if c.get('status') == status]

    def get_by_statuses(self, statuses: List[str]) -> List[Dict[str, Any]]:
        """获取多个状态的候选人."""
        candidates = self.load()
        return [c for c in candidates if c.get('status') in statuses]
