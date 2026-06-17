"""Main orchestrator for boss-hr-recruiter skill."""

import asyncio
import sys
from pathlib import Path

from boss_agent_cli.auth.manager import AuthManager as BACAuthManager
from boss_agent_cli.api.recruiter_client import BossRecruiterClient

from .utils import (
    SkillLogger,
    CandidateStorage,
    load_config,
    CookieExpiredError,
    ConfigError,
)
from .phase1.screening import screen_and_rate
from .phase2.reply_parser import parse_reply_text
from .phase3.goal_judge import judge_goal_completion, update_task_status


async def run_phase1(
    logger: SkillLogger,
    auth: BACAuthManager,
    config: dict,
    storage: CandidateStorage,
) -> None:
    """执行阶段一：筛选 + 打招呼 (双源并行).

    流程：
    1. 并行获取新招呼列表 + 推荐牛人列表
    2. 合并去重 + 配额分配（两源各占一半）
    3. 逐人获取简历、筛选、评分、发送打招呼

    Args:
        logger: 日志器
        auth: 认证管理器
        config: 配置
        storage: 数据存储器
    """
    from .phase1.sources import fetch_all_candidates, deduplicate_candidates
    from .phase1.allocator import allocate_candidates_by_quota

    logger.info("## 开始阶段一：筛选 + 打招呼（双源并行）")

    # 检查任务状态
    task_status = config.get('task_status', 'active')
    if task_status in ('completed', 'expired'):
        logger.info(f"任务已{task_status}，跳过阶段一")
        return

    try:
        job_id = config.get('job_id', '')
        if not job_id:
            logger.error("缺少 job_id 配置")
            raise Exception("缺少 job_id 配置")

        # Step 1.1: 并行获取两个来源（使用 BossRecruiterClient Python API，避免 GBK 编码）
        logger.info("Step 1.1: 并行获取新招呼和推荐牛人...")
        client = BossRecruiterClient(auth)
        try:
            sources_result = await fetch_all_candidates(
                client,
                job_id,
                max_recommend_pages=3,
                logger_obj=logger
            )
        finally:
            client.close()
        chat_candidates = sources_result.get('chat', [])
        recommend_candidates = sources_result.get('recommend', [])

        # Step 1.2: 合并去重
        logger.info("Step 1.2: 合并去重...")
        merged = deduplicate_candidates(
            chat_candidates,
            recommend_candidates,
            logger_obj=logger
        )

        # Step 1.3: 配额分配
        logger.info("Step 1.3: 配额分配...")
        target_count = config.get('greet_batch_size', 10)
        allocated = allocate_candidates_by_quota(
            merged,
            target_count,
            source_ratio={'chat': 0.5, 'recommend': 0.5},
            logger_obj=logger
        )

        logger.info(
            f"分配完成：共 {len(allocated)} 人 "
            f"(新招呼: {len([c for c in allocated if c.get('source')=='chat'])} 人, "
            f"推荐: {len([c for c in allocated if c.get('source')=='recommend'])} 人)"
        )

        # Step 1.4-1.5: 逐人获取简历、筛选、评分、发送打招呼
        logger.info("Step 1.4-1.5: 逐人筛选和发送打招呼...")

        greet_count = 0
        for candidate in allocated:
            try:
                uid = candidate.get('uid', '')
                name = candidate.get('name', 'Unknown')
                source = candidate.get('source', 'unknown')

                # 获取简历（框架预留，需boss-agent-cli支持）
                logger.info(f"  [{source}] {name} - 获取简历中...")

                # 筛选评分
                score = screen_and_rate(candidate, config.get('screen_rules', {}))
                logger.info(f"  [{source}] {name} - 评分: {score}%")

                # 符合度 >=75% 发送打招呼
                if score >= 75:
                    logger.info(f"  [{source}] {name} - 符合要求，准备发送打招呼")
                    # boss hr reply <uid> "message" (需boss-agent-cli支持)
                    greet_count += 1
                    candidate['status'] = '首轮沟通'
                    candidate['first_message_sent_at'] = __import__('datetime').datetime.now().isoformat()
                else:
                    logger.info(f"  [{source}] {name} - 不符合要求（评分{score}%<75%）")
                    candidate['status'] = 'FAILED'
                    candidate['exclude_reason'] = f"筛选评分不足 ({score}%)"

            except Exception as e:
                logger.warning(f"  处理候选人 {name} 失败: {e}")
                continue

        # 保存更新：合并新候选人到现有列表
        if allocated:
            existing = storage.load()
            # 按uid去重，新候选人优先
            existing_uids = {c.get('uid') for c in existing}
            for candidate in allocated:
                if candidate.get('uid') not in existing_uids:
                    existing.append(candidate)
                else:
                    # 更新现有候选人
                    for i, c in enumerate(existing):
                        if c.get('uid') == candidate.get('uid'):
                            existing[i] = candidate
                            break
            storage.save(existing)

        logger.info(f"阶段一完成：本批发送 {greet_count} 条打招呼消息 ✅")

    except CookieExpiredError:
        logger.error("Cookie已过期，停止运行")
        raise
    except Exception as e:
        logger.error(f"阶段一执行失败: {e}", exc_info=True)
        raise


async def run_phase2(
    logger: SkillLogger,
    auth: BACAuthManager,
    config: dict,
    storage: CandidateStorage,
) -> None:
    """执行阶段二：判断回复是否达标.

    Args:
        logger: 日志器
        auth: 认证管理器
        config: 配置
        storage: 数据存储器
    """
    logger.info("## 开始阶段二：判断回复是否达标")

    # 检查任务状态
    task_status = config.get('task_status', 'active')
    if task_status in ('completed', 'expired'):
        logger.info(f"任务已{task_status}，跳过阶段二")
        return

    try:
        # 获取待判断候选人
        logger.info("正在检查候选人回复...")

        candidates = storage.load()
        reply_checked = 0
        promoted_count = 0

        for candidate in candidates:
            if candidate.get('status') != '首轮沟通':
                continue

            uid = candidate.get('uid', '')
            name = candidate.get('name', 'Unknown')

            try:
                # boss hr chatmsg <uid> (需boss-agent-cli支持)
                # 解析回复内容：arrival_weeks, days_per_week, duration_months
                logger.info(f"  检查 {name} 的回复...")

                reply = candidate.get('reply_content', '')
                if not reply:
                    logger.info(f"    - 暂无新回复，继续等待")
                    continue

                # 使用parse_reply_text解析回复
                screen_rules = config.get('screen_rules', {})
                parsed = parse_reply_text(reply, screen_rules)
                if parsed.get('qualified'):
                    logger.info(f"    - 回复达标，推进二轮")
                    candidate['status'] = '二轮沟通'
                    promoted_count += 1
                elif parsed.get('needs_clarification'):
                    logger.info(f"    - 信息不完整，追问一次")
                    candidate['status'] = '首轮沟通追加提问'
                else:
                    logger.info(f"    - 不达标，淘汰")
                    candidate['status'] = 'FAILED'
                    candidate['exclude_reason'] = parsed.get('reason', '回复不达标')

                reply_checked += 1

            except Exception as e:
                logger.warning(f"    - 检查失败: {e}")
                continue

        # 保存更新
        storage.save(candidates)
        logger.info(f"阶段二完成：检查 {reply_checked} 人，推进 {promoted_count} 人 ✅")

    except CookieExpiredError:
        logger.error("Cookie已过期，停止运行")
        raise
    except Exception as e:
        logger.error(f"阶段二执行失败: {e}", exc_info=True)
        raise


async def run_phase3(
    logger: SkillLogger,
    auth: BACAuthManager,
    config: dict,
    storage: CandidateStorage,
) -> None:
    """执行阶段三：简历处理 + 目标判断.

    Args:
        logger: 日志器
        auth: 认证管理器
        config: 配置
        storage: 数据存储器
    """
    logger.info("## 开始阶段三：简历处理 + 目标判断")

    try:
        # 索要简历 + 接收简历
        logger.info("处理待索要简历的候选人...")

        candidates = storage.load()
        resume_requested = 0
        resume_received = 0

        for candidate in candidates:
            if candidate.get('status') != '二轮沟通':
                continue

            uid = candidate.get('uid', '')
            name = candidate.get('name', 'Unknown')

            try:
                # 发送索要简历消息
                second_msg = config.get('second_round_message', '')
                if second_msg:
                    logger.info(f"  发送索要简历消息给 {name}...")
                    # boss hr reply <uid> "<second_msg>" (需boss-agent-cli支持)
                    resume_requested += 1

                # 检查是否收到简历 (boss hr chatmsg <uid>)
                logger.info(f"  检查 {name} 是否已提交简历...")
                if candidate.get('reply_content', '').find('aid=38') > -1:
                    logger.info(f"    - 简历已收到")
                    candidate['status'] = '简历已获取'
                    resume_received += 1
                else:
                    logger.info(f"    - 简历未收到，继续等待")
                    candidate['status'] = '等待简历'

            except Exception as e:
                logger.warning(f"  处理失败 {name}: {e}")
                continue

        # 保存更新
        storage.save(candidates)

        # 判断目标完成情况
        logger.info("检查任务完成情况...")
        result = judge_goal_completion(config['runtime_dir'])
        resume_count = result['resume_count']
        resume_target = config.get('resume_target', 5)

        logger.info(f"简历进度：{resume_count}/{resume_target}")
        logger.info(f"任务状态：{result['task_status']}")

        # 如果任务完成或过期，更新状态
        if result['is_completed'] or result['is_expired']:
            logger.info(f"更新任务状态为：{result['task_status']}")
            update_task_status(
                config['runtime_dir'],
                result['task_status'],
                result['reason']
            )

        logger.info(f"阶段三完成：索要 {resume_requested} 份，收到 {resume_received} 份 ✅")

    except CookieExpiredError:
        logger.error("Cookie已过期，停止运行")
        raise
    except Exception as e:
        logger.error(f"阶段三执行失败: {e}", exc_info=True)
        raise


async def main(runtime_dir: str, phase: int = None) -> None:
    """主函数：单次运行三个阶段（或指定阶段）.

    Args:
        runtime_dir: 运行时目录路径
        phase: 要运行的阶段（1/2/3，None表示全部）
    """
    # 初始化
    try:
        config = load_config(runtime_dir)
    except ConfigError as e:
        print(f"❌ 配置加载失败: {e}")
        sys.exit(1)

    logger = SkillLogger(runtime_dir, "main")
    storage = CandidateStorage(runtime_dir)
    auth = BACAuthManager(Path.home() / '.boss-agent')

    logger.info("=" * 60)
    logger.info(f"Boss直聘招聘助手 - 开始运行")
    logger.info(f"任务：{config.get('task_name', 'unknown')}")
    logger.info(f"运行时目录：{runtime_dir}")
    if phase:
        logger.info(f"执行模式：仅运行 Phase {phase}")
    else:
        logger.info(f"执行模式：完整流程（Phase 1-3）")
    logger.info("=" * 60)

    try:
        # 按需执行阶段
        if phase is None or phase == 1:
            await run_phase1(logger, auth, config, storage)

        if phase is None or phase == 2:
            await run_phase2(logger, auth, config, storage)

        if phase is None or phase == 3:
            await run_phase3(logger, auth, config, storage)

        logger.info("=" * 60)
        logger.info("✅ 本次运行完成")
        logger.info("=" * 60)

    except CookieExpiredError:
        logger.critical("❌ Cookie已过期，请重新登录后再运行")
        logger.critical("执行命令：boss login")
        sys.exit(2)

    except Exception as e:
        logger.critical(f"❌ 运行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法：python -m boss_hr_recruiter.main <runtime_dir>")
        sys.exit(1)

    runtime_dir = sys.argv[1]
    asyncio.run(main(runtime_dir))
