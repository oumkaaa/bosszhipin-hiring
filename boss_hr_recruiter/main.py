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

    logger.info("## Phase 1: Screening + Greeting (dual sources)")

    task_status = config.get('task_status', 'active')
    if task_status in ('completed', 'expired'):
        logger.info(f"Task status: {task_status} - skipping Phase 1")
        return

    try:
        job_id = config.get('job_id', '')
        if not job_id:
            logger.error("Missing job_id config")
            raise Exception("Missing job_id config")

        logger.info("Step 1.1: Fetching candidates (chat + recommend)...")
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

        logger.info("Step 1.2: Deduplicating candidates...")
        merged = deduplicate_candidates(
            chat_candidates,
            recommend_candidates,
            logger_obj=logger
        )

        logger.info("Step 1.3: Allocating quota...")
        target_count = config.get('greet_batch_size', 10)
        allocated = allocate_candidates_by_quota(
            merged,
            target_count,
            source_ratio={'chat': 0.5, 'recommend': 0.5},
            logger_obj=logger
        )

        chat_count = len([c for c in allocated if c.get('source')=='chat'])
        rec_count = len([c for c in allocated if c.get('source')=='recommend'])
        logger.info(f"Allocated {len(allocated)} candidates (chat: {chat_count}, recommend: {rec_count})")

        # Step 1.4-1.5: Screen, rate, and greet candidates
        logger.info("Step 1.4-1.5: Screening, rating, and greeting candidates...")

        # Create client for screening
        client = BossRecruiterClient(auth)
        try:
            greet_count = 0
            for candidate in allocated:
                try:
                    candidate_id = (
                        candidate.get('uid')
                        or candidate.get('friendId')
                        or candidate.get('encryptGeekId')
                        or 'unknown'
                    )
                    name = candidate.get('name', 'Unknown')
                    source = candidate.get('source', 'unknown')

                    logger.info(f"  [{source}] {name} (ID: {candidate_id}) - Screening...")

                    # Screen and rate
                    screen_result = screen_and_rate(
                        candidate=candidate,
                        client=client,
                        config=config,
                        rules=config.get("screen_rules", {}),
                        logger=logger,
                        geek_card=candidate.get("geekCard"),
                    )

                    score = screen_result.get('score', 0.0)
                    logger.info(f"  [{source}] {name} - Score: {score}%")

                    if screen_result['screen_result'] == 'PASS' and score >= 75:
                        logger.info(f"  [{source}] {name} - Qualified, preparing greeting")
                        if not config.get('dry_run', False):
                            logger.info(f"  [DRY-RUN] Would send greeting to {name}")
                        greet_count += 1
                        candidate['status'] = '首轮沟通'
                        from datetime import datetime
                        candidate['first_message_sent_at'] = datetime.now().isoformat()
                    else:
                        logger.info(f"  [{source}] {name} - Not qualified")
                        candidate['status'] = 'FAILED'
                        candidate['exclude_reason'] = screen_result.get('exclude_reason', 'Failed screening')

                    # Merge screen result into candidate
                    candidate.update(screen_result)

                except Exception as e:
                    logger.warning(f"  Failed to process {name}: {e}")
                    continue
        finally:
            client.close()

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

        logger.info(f"Phase 1 done: greeted {greet_count} candidates")

    except CookieExpiredError:
        logger.error("Cookie expired - stopping")
        raise
    except Exception as e:
        logger.error(f"Phase 1 failed: {e}", exc_info=True)
        raise


async def run_phase2(
    logger: SkillLogger,
    auth: BACAuthManager,
    config: dict,
    storage: CandidateStorage,
) -> None:
    """Phase 2: Judge if candidate replies meet criteria.

    Fetches latest messages from agentcli and parses for qualification.

    Args:
        logger: Logger instance
        auth: Auth manager
        config: Config dict
        storage: Candidate storage
    """
    from .adapters import AgentCliAdapter

    logger.info("## Phase 2: Judging replies")

    task_status = config.get('task_status', 'active')
    if task_status in ('completed', 'expired'):
        logger.info(f"Task status: {task_status} - skipping Phase 2")
        return

    adapter = AgentCliAdapter(auth, logger)
    try:
        logger.info("Fetching latest messages from candidates...")

        candidates = storage.load()
        reply_checked = 0
        promoted_count = 0
        follow_up_sent = 0

        for candidate in candidates:
            if candidate.get('status') not in ('首轮沟通', '首轮沟通追加提问'):
                continue

            candidate_id = (
                candidate.get('uid')
                or candidate.get('friendId')
                or candidate.get('friend_id')
                or 'unknown'
            )
            name = candidate.get('name', 'Unknown')
            status = candidate.get('status', 'unknown')

            try:
                logger.info(f"  [{status}] {name}...")

                # Fetch latest messages from agentcli
                messages_result = adapter.get_latest_messages([int(candidate_id)])
                messages = messages_result.get('zpData', {}).get('messages', [])

                if not messages:
                    logger.info(f"    - No new messages")
                    candidate['last_message_checked_at'] = __import__('datetime').datetime.now().isoformat()
                    candidate['last_agentcli_result'] = {
                        'code': messages_result.get('code'),
                        'action': 'get_latest_messages',
                        'message_count': 0
                    }
                    continue

                # Extract reply text from latest message
                latest_msg = messages[0] if messages else {}
                reply = latest_msg.get('content', '')

                if not reply:
                    logger.info(f"    - Latest message empty")
                    candidate['last_message_checked_at'] = __import__('datetime').datetime.now().isoformat()
                    continue

                # Parse reply
                screen_rules = config.get('screen_rules', {})
                parsed = parse_reply_text(reply, screen_rules)

                # Store parsed result
                candidate['parsed_reply'] = {
                    'content': reply,
                    'arrival_weeks': parsed.get('arrival_weeks'),
                    'days_per_week': parsed.get('days_per_week'),
                    'duration_months': parsed.get('duration_months'),
                }
                candidate['last_message_checked_at'] = __import__('datetime').datetime.now().isoformat()
                candidate['last_agentcli_result'] = {
                    'code': messages_result.get('code'),
                    'action': 'get_latest_messages',
                    'message_count': len(messages)
                }

                # Route by qualification
                if parsed.get('qualified'):
                    logger.info(f"    - Reply qualified - advancing to 二轮沟通")
                    candidate['status'] = '二轮沟通'
                    promoted_count += 1

                elif parsed.get('needs_clarification'):
                    # Check if already asked for clarification
                    times_asked = candidate.get('clarification_ask_count', 0)

                    if times_asked == 0:
                        logger.info(f"    - Incomplete - sending follow-up")
                        # Send follow-up message
                        follow_up_msg = config.get('follow_up_message', '')
                        if follow_up_msg and not config.get('dry_run', False):
                            send_result = adapter.send_message(
                                int(candidate_id),
                                follow_up_msg,
                                dry_run=config.get('dry_run', False)
                            )
                            candidate['last_agentcli_result'] = {
                                'code': send_result.get('code'),
                                'action': 'send_message',
                                'message_type': 'follow_up'
                            }
                            candidate['follow_up_sent_at'] = __import__('datetime').datetime.now().isoformat()
                        candidate['status'] = '首轮沟通追加提问'
                        candidate['clarification_ask_count'] = 1
                        follow_up_sent += 1
                    else:
                        logger.info(f"    - Still incomplete after follow-up - rejecting")
                        reject_msg = config.get('reject_message', '')
                        if reject_msg and not config.get('dry_run', False):
                            send_result = adapter.send_message(
                                int(candidate_id),
                                reject_msg,
                                dry_run=config.get('dry_run', False)
                            )
                            candidate['last_agentcli_result'] = {
                                'code': send_result.get('code'),
                                'action': 'send_message',
                                'message_type': 'reject'
                            }
                            candidate['reject_sent_at'] = __import__('datetime').datetime.now().isoformat()
                        candidate['status'] = 'FAILED'
                        candidate['exclude_reason'] = 'Reply incomplete after follow-up'

                else:
                    logger.info(f"    - Not qualified - rejecting")
                    reject_msg = config.get('reject_message', '')
                    if reject_msg and not config.get('dry_run', False):
                        send_result = adapter.send_message(
                            int(candidate_id),
                            reject_msg,
                            dry_run=config.get('dry_run', False)
                        )
                        candidate['last_agentcli_result'] = {
                            'code': send_result.get('code'),
                            'action': 'send_message',
                            'message_type': 'reject'
                        }
                        candidate['reject_sent_at'] = __import__('datetime').datetime.now().isoformat()
                    candidate['status'] = 'FAILED'
                    candidate['exclude_reason'] = parsed.get('reason', 'Reply not qualified')

                reply_checked += 1

            except Exception as e:
                logger.warning(f"    - Check failed: {e}")
                candidate['last_agentcli_result'] = {
                    'code': -1,
                    'action': 'get_latest_messages',
                    'error': str(e)
                }
                continue

        storage.save(candidates)
        logger.info(f"Phase 2 done: checked {reply_checked}, advanced {promoted_count}, follow-up sent {follow_up_sent}")

    except CookieExpiredError:
        logger.error("Cookie expired - stopping")
        raise
    except Exception as e:
        logger.error(f"Phase 2 failed: {e}", exc_info=True)
        raise
    finally:
        adapter.close()


async def run_phase3(
    logger: SkillLogger,
    auth: BACAuthManager,
    config: dict,
    storage: CandidateStorage,
) -> None:
    """Phase 3: Resume handling + goal completion check.

    Requests resumes from 二轮沟通 candidates and checks for receipt.

    Args:
        logger: Logger instance
        auth: Auth manager
        config: Config dict
        storage: Candidate storage
    """
    from .adapters import AgentCliAdapter

    logger.info("## Phase 3: Resume handling + goal check")

    adapter = AgentCliAdapter(auth, logger)
    try:
        logger.info("Processing candidates needing resumes...")

        candidates = storage.load()
        resume_requested = 0
        resume_received = 0

        # Track which candidates are waiting for resume
        waiting_candidates = [c for c in candidates if c.get('status') == '等待简历']
        new_candidates = [c for c in candidates if c.get('status') == '二轮沟通']

        # Process new candidates: request resume
        for candidate in new_candidates:
            candidate_id = (
                candidate.get('uid')
                or candidate.get('friendId')
                or candidate.get('friend_id')
                or 'unknown'
            )
            name = candidate.get('name', 'Unknown')

            try:
                logger.info(f"  Requesting resume from {name}...")

                # First, send the second round message (if configured)
                second_msg = config.get('second_round_message', '')
                if second_msg and not config.get('dry_run', False):
                    send_result = adapter.send_message(
                        int(candidate_id),
                        second_msg,
                        dry_run=config.get('dry_run', False)
                    )
                    candidate['last_agentcli_result'] = {
                        'code': send_result.get('code'),
                        'action': 'send_message',
                        'message_type': 'second_round'
                    }

                # Then request resume via exchange API
                request_result = adapter.request_resume(
                    int(candidate_id),
                    dry_run=config.get('dry_run', False)
                )

                if request_result.get('code') == 0 or request_result.get('dry_run'):
                    logger.info(f"    - Resume request sent")
                    candidate['status'] = '等待简历'
                    candidate['resume_requested_at'] = __import__('datetime').datetime.now().isoformat()
                    candidate['resume_request_result'] = {
                        'code': request_result.get('code'),
                        'action': 'exchange_request_by_friend'
                    }
                    resume_requested += 1
                else:
                    logger.warning(f"    - Resume request failed: {request_result.get('message')}")
                    candidate['last_agentcli_result'] = {
                        'code': request_result.get('code'),
                        'action': 'exchange_request_by_friend',
                        'error': request_result.get('message')
                    }

            except Exception as e:
                logger.warning(f"  Failed to request resume from {name}: {e}")
                candidate['last_agentcli_result'] = {
                    'code': -1,
                    'action': 'exchange_request_by_friend',
                    'error': str(e)
                }
                continue

        # Process waiting candidates: check for receipt
        for candidate in waiting_candidates:
            candidate_id = (
                candidate.get('uid')
                or candidate.get('friendId')
                or candidate.get('friend_id')
                or 'unknown'
            )
            name = candidate.get('name', 'Unknown')

            try:
                logger.info(f"  Checking if {name} submitted resume...")

                # Fetch latest messages
                messages_result = adapter.get_latest_messages([int(candidate_id)])
                messages = messages_result.get('zpData', {}).get('messages', [])

                if not messages:
                    logger.info(f"    - No new messages")
                    candidate['last_message_checked_at'] = __import__('datetime').datetime.now().isoformat()
                    continue

                # Check if any message contains resume (aid=38 indicates resume exchange)
                resume_received_flag = False
                for msg in messages:
                    content = msg.get('content', '')
                    if 'aid=38' in content or 'attachment' in content.lower():
                        resume_received_flag = True
                        break

                if resume_received_flag:
                    logger.info(f"    - Resume received")
                    candidate['status'] = '简历已获取'
                    candidate['resume_received_at'] = __import__('datetime').datetime.now().isoformat()
                    resume_received += 1
                else:
                    logger.info(f"    - No resume yet, still waiting...")
                    candidate['status'] = '等待简历'

                candidate['last_message_checked_at'] = __import__('datetime').datetime.now().isoformat()
                candidate['last_agentcli_result'] = {
                    'code': messages_result.get('code'),
                    'action': 'get_latest_messages',
                    'message_count': len(messages)
                }

            except Exception as e:
                logger.warning(f"  Failed to check resume for {name}: {e}")
                candidate['last_agentcli_result'] = {
                    'code': -1,
                    'action': 'get_latest_messages',
                    'error': str(e)
                }
                continue

        storage.save(candidates)

        logger.info("Checking goal completion...")
        result = judge_goal_completion(config['runtime_dir'])
        resume_count = result['resume_count']
        resume_target = config.get('resume_target', 5)

        logger.info(f"Resume progress: {resume_count}/{resume_target}")
        logger.info(f"Task status: {result['task_status']}")

        if result['is_completed'] or result['is_expired']:
            logger.info(f"Updating task status to: {result['task_status']}")
            update_task_status(
                config['runtime_dir'],
                result['task_status'],
                result['reason']
            )

        logger.info(f"Phase 3 done: requested {resume_requested}, received {resume_received}")

    except CookieExpiredError:
        logger.error("Cookie expired - stopping")
        raise
    except Exception as e:
        logger.error(f"Phase 3 failed: {e}", exc_info=True)
        raise
    finally:
        adapter.close()


async def main(runtime_dir: str, phase: int = None, dry_run: bool = False) -> None:
    """Main orchestrator: run one or all phases.

    Args:
        runtime_dir: Runtime directory path
        phase: Specific phase to run (1/2/3, None for all)
        dry_run: Simulate without sending real messages
    """
    from .adapters import AgentCliAdapter

    try:
        config = load_config(runtime_dir)
    except ConfigError as e:
        print(f"Config load failed: {e}")
        sys.exit(1)

    config['dry_run'] = dry_run
    logger = SkillLogger(runtime_dir, "main")
    storage = CandidateStorage(runtime_dir)
    auth = BACAuthManager(Path.home() / '.boss-agent')

    logger.info("=" * 60)
    logger.info(f"Boss Zhipin Hiring Assistant - Starting")
    logger.info(f"Task: {config.get('task_name', 'unknown')}")
    logger.info(f"Runtime dir: {runtime_dir}")
    if dry_run:
        logger.info("Mode: DRY-RUN (simulated, no real messages)")
    if phase:
        logger.info(f"Phases: {phase} only")
    else:
        logger.info("Phases: all (1-3)")
    logger.info("=" * 60)

    # Preflight auth check
    logger.info("\nPreflight: Checking authentication...")
    adapter = AgentCliAdapter(auth, logger)
    try:
        auth_result = adapter.check_auth_status()
        auth_code = auth_result.get('code', -1)

        if auth_code in (7, 37):
            logger.critical("Auth failed: Cookie expired - please re-login")
            logger.critical("Run: boss login --cdp")
            sys.exit(2)

        if auth_code != 0:
            logger.critical(f"Auth check failed (code {auth_code}): {auth_result.get('message')}")
            sys.exit(2)

        logger.info("Auth OK - proceeding")

        # Check send allowance
        if not config.get('dry_run', False) and not config.get('allow_send', False):
            logger.warning("WARNING: allow_send=false, running in dry-run mode")
            config['dry_run'] = True

    except Exception as e:
        logger.critical(f"Preflight auth check failed: {e}")
        sys.exit(2)
    finally:
        adapter.close()

    try:
        # 按需执行阶段
        if phase is None or phase == 1:
            await run_phase1(logger, auth, config, storage)

        if phase is None or phase == 2:
            await run_phase2(logger, auth, config, storage)

        if phase is None or phase == 3:
            await run_phase3(logger, auth, config, storage)

        logger.info("=" * 60)
        logger.info("Run completed successfully")
        logger.info("=" * 60)

    except CookieExpiredError:
        logger.critical("Cookie expired - please re-login and try again")
        logger.critical("Run: boss login --cdp")
        sys.exit(2)

    except Exception as e:
        logger.critical(f"Run failed: {e}", exc_info=True)
        sys.exit(1)
