"""Goal judgment for Phase 3."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ..utils.config import load_config


def judge_goal_completion(runtime_dir: str) -> Dict[str, Any]:
    """判断整体招聘目标是否达成.

    Args:
        runtime_dir: 运行时目录

    Returns:
        {
            'is_completed': bool,
            'is_expired': bool,
            'resume_count': int,
            'resume_target': int,
            'task_status': str,
            'reason': str,
        }
    """
    runtime_path = Path(runtime_dir)

    # 加载配置
    config = load_config(runtime_dir)
    resume_target = config.get('resume_target', 20)
    task_deadline = config.get('task_deadline', '')
    current_task_status = config.get('task_status', 'active')

    # 统计简历数
    candidates_file = runtime_path / 'candidates.json'
    resume_count = 0

    if candidates_file.exists():
        with open(candidates_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            candidates = data.get('candidates', [])
            resume_count = sum(1 for c in candidates if c.get('status') == '简历已获取')

    # 判断目标是否达成
    is_completed = False
    is_expired = False
    reason = ''
    new_status = current_task_status

    if current_task_status == 'active':
        # 检查是否达到简历数目标
        if resume_count >= resume_target:
            is_completed = True
            new_status = 'completed'
            reason = f'简历数达标（{resume_count}/{resume_target}）'
        else:
            # Check if deadline passed (handle aware/naive datetime properly)
            if task_deadline:
                try:
                    deadline_dt = datetime.fromisoformat(task_deadline)
                    # Handle timezone-aware deadline vs naive now()
                    if deadline_dt.tzinfo:
                        now = datetime.now(deadline_dt.tzinfo)
                    else:
                        now = datetime.now()

                    if now > deadline_dt:
                        is_expired = True
                        new_status = 'expired'
                        reason = 'Deadline passed'
                except Exception as e:
                    # Log but don't fail - deadline check is optional
                    pass

    return {
        'is_completed': is_completed,
        'is_expired': is_expired,
        'resume_count': resume_count,
        'resume_target': resume_target,
        'task_status': new_status,
        'reason': reason,
    }


def update_task_status(runtime_dir: str, new_status: str, reason: str = '') -> None:
    """更新任务状态.

    Args:
        runtime_dir: 运行时目录
        new_status: 新状态（completed/expired/manual_stopped）
        reason: 停止原因
    """
    runtime_path = Path(runtime_dir)
    context_file = runtime_path / 'run-context.json'

    if not context_file.exists():
        return

    with open(context_file, 'r', encoding='utf-8') as f:
        context = json.load(f)

    context['task_status'] = new_status
    context['task_completed_at'] = datetime.now().isoformat()
    context['task_stop_reason'] = reason or new_status

    # 原子写入
    tmp_file = runtime_path / 'run-context.json.tmp'
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(context, f, ensure_ascii=False, indent=2)
        f.write('\n')

    tmp_file.replace(context_file)
