"""Fetch candidates from dual sources: chat list and recommend list.

完全使用 boss-agent-cli 的 Python API，避免子进程和 GBK 编码问题。
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


async def fetch_chat_list_candidates(
    client: Any,
    job_id: str,
    logger_obj: Any = None
) -> List[Dict[str, Any]]:
    """获取新招呼列表（使用 Python API）.

    Args:
        client: BossRecruiterClient 实例
        job_id: 职位ID（如 '543926518'）
        logger_obj: 日志对象

    Returns:
        候选人列表 [{'friendId': int, 'name': str, 'source': 'chat'}, ...]
    """
    if logger_obj is None:
        logger_obj = logger

    try:
        logger_obj.info("正在获取新招呼列表（friend_list API）...")

        # 使用 BossRecruiterClient.friend_list() API 获取新招呼
        # label_id=1 表示"新招呼"
        result = client.friend_list(page=1, label_id=1, job_id=job_id)

        if result.get('code') != 0:
            logger_obj.warning(f"friend_list 返回错误: {result.get('message', 'unknown error')}")
            return []

        friends = (result.get('zpData') or {}).get('friendList') or []
        chat_candidates = []

        for friend in friends:
            candidate = {
                'friendId': friend.get('uid') or friend.get('friendId'),
                'name': friend.get('name', ''),
                'source': 'chat'
            }
            chat_candidates.append(candidate)

        logger_obj.info(f"新招呼列表：{len(chat_candidates)} 人")
        return chat_candidates

    except Exception as e:
        logger_obj.error(f"获取新招呼列表失败: {e}", exc_info=True)
        return []


async def fetch_recommend_candidates(
    client: Any,
    job_id: str,
    max_pages: int = 3,
    logger_obj: Any = None
) -> List[Dict[str, Any]]:
    """获取推荐牛人列表（使用 Python API，支持分页）.

    Args:
        client: BossRecruiterClient 实例
        job_id: 职位ID（如 '543926518'）
        max_pages: 最多获取页数
        logger_obj: 日志对象

    Returns:
        推荐候选人列表 [{'encryptGeekId': str, 'name': str, 'geekCard': {...}, 'source': 'recommend'}, ...]
    """
    if logger_obj is None:
        logger_obj = logger

    try:
        logger_obj.info("正在获取推荐牛人列表（greet_rec_list API）...")

        recommend_candidates = []

        # 使用 BossRecruiterClient.greet_rec_list() API 获取打招呼推荐
        # 支持分页
        for page in range(1, max_pages + 1):
            result = client.greet_rec_list(page=page, job_id=job_id)

            if result.get('code') != 0:
                logger_obj.warning(
                    f"greet_rec_list page={page} 返回错误: {result.get('message', 'unknown error')}"
                )
                break

            geeks = (result.get('zpData') or {}).get('geeks') or []
            if not geeks:
                logger_obj.info(f"第 {page} 页无更多推荐牛人")
                break

            for geek in geeks:
                geek_card = geek.get('geekCard', {})
                candidate = {
                    'encryptGeekId': geek_card.get('encryptGeekId', ''),
                    'name': geek_card.get('name', ''),
                    'geekCard': geek_card,  # 保留完整的 geekCard，用于后续简历解析
                    'source': 'recommend'
                }
                recommend_candidates.append(candidate)

            # 检查是否有更多页
            has_more = (result.get('zpData') or {}).get('hasMore', False)
            if not has_more:
                logger_obj.info(f"第 {page} 页已是最后一页")
                break

        logger_obj.info(f"推荐牛人列表：{len(recommend_candidates)} 人（共 {page} 页）")
        return recommend_candidates

    except Exception as e:
        logger_obj.error(f"获取推荐牛人列表失败: {e}", exc_info=True)
        return []


async def fetch_all_candidates(
    client: Any,
    job_id: str,
    max_recommend_pages: int = 3,
    logger_obj: Any = None
) -> Dict[str, List[Dict[str, Any]]]:
    """并行获取两个来源，合并去重.

    Args:
        client: boss-agent-cli 客户端
        job_id: 职位ID
        max_recommend_pages: 推荐列表最多页数
        logger_obj: 日志对象

    Returns:
        按来源分组的候选人字典
        {
            'chat': [{'friendId': int, 'name': str, 'source': 'chat'}, ...],
            'recommend': [{'encryptGeekId': str, 'name': str, 'source': 'recommend'}, ...]
        }
    """
    if logger_obj is None:
        logger_obj = logger

    logger_obj.info("开始并行获取两个候选人来源...")

    # 并行获取两个来源
    chat_results, recommend_results = await asyncio.gather(
        fetch_chat_list_candidates(client, job_id, logger_obj),
        fetch_recommend_candidates(client, job_id, max_recommend_pages, logger_obj),
        return_exceptions=True
    )

    # 处理异常
    if isinstance(chat_results, Exception):
        logger_obj.error(f"新招呼列表获取失败: {chat_results}")
        chat_results = []

    if isinstance(recommend_results, Exception):
        logger_obj.error(f"推荐牛人列表获取失败: {recommend_results}")
        recommend_results = []

    # 添加来源标签
    for candidate in chat_results:
        candidate['source'] = 'chat'

    for candidate in recommend_results:
        candidate['source'] = 'recommend'

    logger_obj.info(
        f"并行获取完成 → 新招呼: {len(chat_results)} 人, 推荐: {len(recommend_results)} 人"
    )

    return {
        'chat': chat_results,
        'recommend': recommend_results
    }


def deduplicate_candidates(
    chat_candidates: List[Dict[str, Any]],
    recommend_candidates: List[Dict[str, Any]],
    logger_obj: Any = None
) -> List[Dict[str, Any]]:
    """合并两个来源的候选人，去除重复.

    Args:
        chat_candidates: 新招呼列表
        recommend_candidates: 推荐列表
        logger_obj: 日志对象

    Returns:
        去重后的合并列表
    """
    if logger_obj is None:
        logger_obj = logger

    # 使用 friendId 和 encryptGeekId 作为唯一标识
    seen_friend_ids = set()
    seen_geek_ids = set()
    merged = []
    duplicates = 0

    for candidate in chat_candidates:
        friend_id = candidate.get('friendId')
        if friend_id and friend_id not in seen_friend_ids:
            seen_friend_ids.add(friend_id)
            merged.append(candidate)

    for candidate in recommend_candidates:
        geek_id = candidate.get('encryptGeekId')
        # 检查是否已经在新招呼中（如果有 friendId）
        if friend_id := candidate.get('friendId'):
            if friend_id in seen_friend_ids:
                duplicates += 1
                continue

        if geek_id and geek_id not in seen_geek_ids:
            seen_geek_ids.add(geek_id)
            merged.append(candidate)
        else:
            duplicates += 1

    if duplicates > 0:
        logger_obj.info(f"去重完成：共 {duplicates} 个重复候选人")

    return merged
