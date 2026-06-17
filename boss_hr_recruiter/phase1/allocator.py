"""Allocate candidates by quota from dual sources."""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def allocate_candidates_by_quota(
    candidates: List[Dict[str, Any]],
    target_count: int,
    source_ratio: Optional[Dict[str, float]] = None,
    logger_obj: Any = None
) -> List[Dict[str, Any]]:
    """按来源分配配额.

    Args:
        candidates: 合并后的候选人列表（含 source 字段）
        target_count: 目标打招呼人数
        source_ratio: 来源比例，如 {'chat': 0.5, 'recommend': 0.5}
        logger_obj: 日志对象

    Returns:
        按配额分配后的候选人列表
    """
    if logger_obj is None:
        logger_obj = logger

    if source_ratio is None:
        source_ratio = {'chat': 0.5, 'recommend': 0.5}

    # 按 source 分组
    by_source = {'chat': [], 'recommend': []}
    for candidate in candidates:
        source = candidate.get('source', 'chat')
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(candidate)

    logger_obj.info(
        f"配额分配：target={target_count}, "
        f"chat={len(by_source['chat'])}, recommend={len(by_source['recommend'])}"
    )

    # 按比例分配
    allocated = []
    for source, ratio in source_ratio.items():
        count = max(1, int(target_count * ratio))  # 至少分配1个
        source_candidates = by_source.get(source, [])

        # 按优先级排序（推荐中按活跃度，新招呼按分数）
        if source == 'recommend':
            # 推荐中按活跃度排序：刚刚活跃 > 今日活跃 > 3日内活跃
            activity_order = {'刚刚活跃': 0, '今日活跃': 1, '3日内活跃': 2}
            source_candidates = sorted(
                source_candidates,
                key=lambda x: (
                    activity_order.get(x.get('activeDesc', ''), 999),
                    x.get('name', '')
                )
            )
        else:
            # 新招呼按得分排序（高分优先）
            source_candidates = sorted(
                source_candidates,
                key=lambda x: (-x.get('score', 0), x.get('name', ''))
            )

        # 截断到配额
        selected = source_candidates[:count]
        allocated.extend(selected)

        logger_obj.info(
            f"从 {source} 分配 {len(selected)} 人"
            f"（可用 {len(source_candidates)} 人，配额 {count} 人）"
        )

    # 如果分配不足，补充不足部分
    if len(allocated) < target_count:
        deficit = target_count - len(allocated)
        allocated_set = {
            c.get('friendId') or c.get('encryptGeekId')
            for c in allocated
        }
        for candidate in candidates:
            if deficit <= 0:
                break
            candidate_id = candidate.get('friendId') or candidate.get('encryptGeekId')
            if candidate_id not in allocated_set:
                allocated.append(candidate)
                allocated_set.add(candidate_id)
                deficit -= 1

        if deficit > 0:
            logger_obj.warning(f"无法补足配额：仍缺 {deficit} 人")

    logger_obj.info(
        f"配额分配完成：{len(allocated)} / {target_count} 人 "
        f"(来自 {len([c for c in allocated if c.get('source')=='chat'])} 个新招呼, "
        f"{len([c for c in allocated if c.get('source')=='recommend'])} 个推荐)"
    )

    return allocated[:target_count]
