"""Data models for Phase 1 screening."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Candidate:
    """招聘候选人数据模型."""
    friend_id: Optional[int] = None  # 新招呼来源：friendId
    encrypt_geek_id: Optional[str] = None  # 推荐来源：encryptGeekId
    source: str = "chat"  # 'chat' | 'recommend'

    name: str = ""
    uid: str = ""
    degree: str = ""  # 本科/硕士/博士
    grad_year: int = 0  # 毕业届别
    screen_result: str = "UNCERTAIN"  # PASS/FAIL/UNCERTAIN
    score: float = 0.0  # 0-100

    work_history: List[str] = field(default_factory=list)
    education: List[str] = field(default_factory=list)
    security_id: Optional[str] = None  # 用于后续请求
    job_id: Optional[str] = None
    exclude_reason: Optional[str] = None  # 不通过原因
    notes: Optional[str] = None
    created_at: Optional[str] = None
    first_message_sent_at: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            'friend_id': self.friend_id,
            'encrypt_geek_id': self.encrypt_geek_id,
            'source': self.source,
            'uid': self.uid,
            'name': self.name,
            'degree': self.degree,
            'grad_year': self.grad_year,
            'screen_result': self.screen_result,
            'score': self.score,
            'work_history': self.work_history,
            'education': self.education,
            'security_id': self.security_id,
            'job_id': self.job_id,
            'exclude_reason': self.exclude_reason,
            'notes': self.notes,
            'created_at': self.created_at,
            'first_message_sent_at': self.first_message_sent_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Candidate':
        """从字典创建."""
        return cls(
            friend_id=data.get('friend_id'),
            encrypt_geek_id=data.get('encrypt_geek_id'),
            source=data.get('source', 'chat'),
            uid=data.get('uid', ''),
            name=data.get('name', ''),
            degree=data.get('degree', ''),
            grad_year=data.get('grad_year', 0),
            screen_result=data.get('screen_result', 'UNCERTAIN'),
            score=data.get('score', 0.0),
            work_history=data.get('work_history', []),
            education=data.get('education', []),
            security_id=data.get('security_id'),
            job_id=data.get('job_id'),
            exclude_reason=data.get('exclude_reason'),
            notes=data.get('notes'),
            created_at=data.get('created_at'),
            first_message_sent_at=data.get('first_message_sent_at'),
        )
