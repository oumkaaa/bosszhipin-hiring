"""Resume screening and rating for Phase 1."""

import re
from typing import Any, Dict, List, Tuple, Optional

from ..utils.logger import SkillLogger


def parse_resume_json(resume_raw: Dict[str, Any]) -> Dict[str, Any]:
    """从boss-agent-cli的--raw JSON中提取关键字段.

    Args:
        resume_raw: hr resume --raw 返回的JSON

    Returns:
        {
            'degree': '本科',  # geekBaseInfo.degreeCategory
            'grad_year': 2028,  # 从 workYearDesc 提取
            'work_history': [...],  # geekWorkExpList
            'education': [...],  # geekEduExpList (含学校、tags)
            'all_text': '...',  # 拼合所有文本用于关键词检查
        }
    """
    data = resume_raw.get('data', {})
    zp_data = data.get('zpData', {})
    geek = zp_data.get('geekDetailInfo', {})
    base = geek.get('geekBaseInfo', {})

    # 学历
    degree = base.get('degreeCategory', '')

    # 毕业届别 - 从 workYearDesc 提取
    # 格式如 "28年应届生" 或 "28年工作"
    work_year_desc = base.get('workYearDesc', '')
    grad_year = 0
    if work_year_desc:
        match = re.search(r'(\d{2})年', work_year_desc)
        if match:
            year_code = int(match.group(1))
            # 22-26届 对应 2022-2026，27届对应2027等
            grad_year = 2000 + year_code

    # 工作经历
    work_list = geek.get('geekWorkExpList', [])
    work_history = []
    for w in work_list:
        text = f"{w.get('companyFullName', '')} - {w.get('positionName', '')}"
        if text.strip() != ' - ':
            work_history.append(text)

    # 教育经历
    edu_list = geek.get('geekEduExpList', [])
    education = []
    edu_tags = []
    for e in edu_list:
        school = e.get('schoolName', '')
        major = e.get('majorName', '')
        text = f"{school} - {major}"
        if text.strip() != ' - ':
            education.append(text)

        # 收集tags（如211/985）
        tags = e.get('tags', [])
        if tags:
            edu_tags.extend(tags)

    # 拼合所有文本用于关键词检查
    all_text = ' '.join([
        degree,
        work_year_desc,
        ' '.join(work_history),
        ' '.join(education),
        ' '.join(edu_tags),
    ])

    return {
        'degree': degree,
        'grad_year': grad_year,
        'work_history': work_history,
        'education': education,
        'edu_tags': edu_tags,
        'all_text': all_text,
        'work_year_desc': work_year_desc,
    }


def parse_recommend_geek_json(geek_card: Dict[str, Any]) -> Dict[str, Any]:
    """从推荐牛人的geekCard中提取关键字段.

    Args:
        geek_card: hr candidates返回的geekCard

    Returns:
        {
            'degree': '本科',  # highestDegreeName
            'grad_year': 2028,  # 从 workYear 提取
            'work_history': [],
            'education': [],  # [school, major]
            'edu_tags': [],
            'all_text': '...',
            'work_year_desc': '28年应届',
        }
    """
    # 学历
    degree = geek_card.get('highestDegreeName', '')

    # 毕业届别 - 从 workYear 提取
    # 格式如 "应届" 或 "28年应届" 或 "5年经验"
    work_year = geek_card.get('workYear', '')
    grad_year = 0
    if work_year:
        match = re.search(r'(\d{2})年', work_year)
        if match:
            year_code = int(match.group(1))
            grad_year = 2000 + year_code

    # 教育信息
    school = geek_card.get('eduSchool', '')
    major = geek_card.get('eduMajor', '')
    education = []
    if school and major:
        education.append(f"{school} - {major}")
    elif school:
        education.append(school)

    # 工作经验（推荐列表中较少详细信息）
    work_history = []
    current_job = geek_card.get('current', {})
    if current_job and current_job.get('name'):
        work_history.append(f"当前：{current_job['name']}")

    # 标签
    edu_tags = []

    # 拼合所有文本用于关键词检查
    all_text = ' '.join([
        degree,
        work_year,
        school,
        major,
        ' '.join(work_history),
        geek_card.get('activeDesc', ''),
    ])

    return {
        'degree': degree,
        'grad_year': grad_year,
        'work_history': work_history,
        'education': education,
        'edu_tags': edu_tags,
        'all_text': all_text,
        'work_year_desc': work_year,
    }


def screen_by_education(
    resume_data: Dict[str, Any],
    rules: Dict[str, Any]
) -> Tuple[bool, str]:
    """基础学历筛选.

    Args:
        resume_data: 解析后的简历数据
        rules: 筛选规则

    Returns:
        (是否通过, 不通过原因)
    """
    degree = resume_data.get('degree', '')
    grad_year = resume_data.get('grad_year', 0)
    all_text = resume_data.get('all_text', '')

    # 学历要求
    valid_degrees = rules.get('valid_degrees', ['本科', '硕士', '博士'])
    if degree not in valid_degrees:
        return False, f"学历不符：{degree}（要求：{','.join(valid_degrees)}）"

    # 届别要求
    min_grad_year = rules.get('min_grad_year', 2026)
    if grad_year < min_grad_year:
        return False, f"届别不符：{grad_year}届（要求：{min_grad_year}届及以后）"

    # 排除关键词
    exclude_keywords = rules.get('exclude_keywords', [
        '专升本', '成人教育', '自考', '电大', '函授'
    ])
    for keyword in exclude_keywords:
        if keyword in all_text:
            return False, f"命中排除关键词：{keyword}"

    return True, ""


def score_business_rules(
    resume_data: Dict[str, Any],
    rules: Dict[str, Any]
) -> float:
    """业务规则评分.

    Args:
        resume_data: 解析后的简历数据
        rules: 评分规则

    Returns:
        0-100的分数
    """
    all_text = resume_data.get('all_text', '')
    edu_tags = resume_data.get('edu_tags', [])

    include_rules = rules.get('business_include_rules', [])
    exclude_rules = rules.get('business_exclude_rules', [])

    # 如果没有设置业务规则，默认返回75
    if not include_rules and not exclude_rules:
        return 75.0

    # 命中排除规则 → 0%
    for rule in exclude_rules:
        if rule in all_text:
            return 0.0

    # 计算包含规则匹配数
    matched = 0
    for rule in include_rules:
        if rule in all_text or any(rule in tag for tag in edu_tags):
            matched += 1

    # 匹配全部 → 100%
    if matched == len(include_rules):
        return 100.0

    # 匹配部分 → 50% + 匹配比例 * 50%
    if len(include_rules) > 0:
        return 50.0 + (matched / len(include_rules)) * 50.0

    # 无实习经历但无负面项 → 60%
    if '实习' not in all_text and '经历' not in all_text:
        return 60.0

    return 75.0


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ''):
            return value
    return None


def _candidate_geek_id(candidate: Dict[str, Any], friend_data: Dict[str, Any]) -> Any:
    return _first_present(
        candidate.get('encryptGeekId'),
        candidate.get('encryptUid'),
        friend_data.get('encryptGeekId'),
        friend_data.get('encryptUid'),
        friend_data.get('encryptFriendId'),
    )


def _candidate_job_id(candidate: Dict[str, Any], friend_data: Dict[str, Any], config: Dict[str, Any]) -> Any:
    return _first_present(
        candidate.get('encryptJobId'),
        candidate.get('encJobId'),
        friend_data.get('encryptJobId'),
        friend_data.get('encJobId'),
        config.get('encrypt_job_id'),
        config.get('encryptJobId'),
    )


def _candidate_security_id(candidate: Dict[str, Any], friend_data: Dict[str, Any]) -> Any:
    return _first_present(
        candidate.get('securityId'),
        candidate.get('security_id'),
        friend_data.get('securityId'),
        friend_data.get('security_id'),
    )


def screen_and_rate(
    candidate: Dict[str, Any],
    client: Any,
    config: Dict[str, Any],
    rules: Dict[str, Any],
    logger: SkillLogger,
    geek_card: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """对单个候选人进行筛选和评分 (支持两个来源，使用 Python API 获取简历).

    Args:
        candidate: 候选人信息字典（含 source、name、friendId/encryptGeekId）
        client: BossRecruiterClient 实例
        config: 运行时配置（含 job_id）
        rules: 筛选和评分规则
        logger: 日志器
        geek_card: 推荐牛人的geekCard（可选）

    Returns:
        {
            'name': str,
            'source': 'chat'|'recommend',
            'screen_result': 'PASS'/'FAIL'/'UNCERTAIN',
            'score': float,
            'resume_data': dict,
            'exclude_reason': str,
        }
    """
    name = candidate.get('name', 'Unknown')
    source = candidate.get('source', 'chat')

    try:
        # 根据来源获取加密的 geek_id 和 job_id
        if source == 'chat':
            friend_id = candidate.get('friendId')
            if not friend_id:
                return {
                    'name': name,
                    'source': source,
                    'screen_result': 'UNCERTAIN',
                    'score': 0.0,
                    'resume_data': {},
                    'exclude_reason': 'missing friendId',
                }

            friend_data: Dict[str, Any] = {}
            geek_id = _candidate_geek_id(candidate, friend_data)
            job_id = _candidate_job_id(candidate, friend_data, config)
            security_id = _candidate_security_id(candidate, friend_data)

            if not geek_id or not job_id:
                friend_detail_resp = client.friend_detail([friend_id])
                if friend_detail_resp.get('code') != 0:
                    logger.warning(f"{name} friend_detail failed: {friend_detail_resp.get('message')}")
                    return {
                        'name': name,
                        'source': source,
                        'screen_result': 'UNCERTAIN',
                        'score': 0.0,
                        'resume_data': {},
                        'exclude_reason': f"friend_detail failed: {friend_detail_resp.get('message')}",
                    }

                friends = friend_detail_resp.get('zpData', {}).get('friendList', [])
                if not friends:
                    return {
                        'name': name,
                        'source': source,
                        'screen_result': 'UNCERTAIN',
                        'score': 0.0,
                        'resume_data': {},
                        'exclude_reason': 'friend_detail returned no candidate data',
                    }

                friend_data = friends[0]
                geek_id = _candidate_geek_id(candidate, friend_data)
                job_id = _candidate_job_id(candidate, friend_data, config)
                security_id = _candidate_security_id(candidate, friend_data)

            if not geek_id or not job_id:
                missing = []
                if not geek_id:
                    missing.append('encryptGeekId/encryptUid')
                if not job_id:
                    missing.append('encryptJobId/encJobId')
                return {
                    'name': name,
                    'source': source,
                    'screen_result': 'UNCERTAIN',
                    'score': 0.0,
                    'resume_data': {},
                    'exclude_reason': f"missing {', '.join(missing)}",
                }

            logger.debug(f"Fetching resume for {name} (geek_id={str(geek_id)[:20]}...)")
            resume_resp = client.view_geek(geek_id, job_id, security_id)

            if resume_resp.get('code') != 0:
                logger.warning(f"{name} resume fetch failed: {resume_resp.get('message')}")
                return {
                    'name': name,
                    'source': source,
                    'screen_result': 'UNCERTAIN',
                    'score': 0.0,
                    'resume_data': {},
                    'exclude_reason': f"resume fetch failed: {resume_resp.get('message')}",
                }

            resume_data = parse_resume_json(resume_resp)

        else:
            # 推荐：从 geekCard 直接解析
            if geek_card:
                resume_data = parse_recommend_geek_json(geek_card)
            else:
                return {
                    'name': name,
                    'source': source,
                    'screen_result': 'UNCERTAIN',
                    'score': 0.0,
                    'resume_data': {},
                    'exclude_reason': '无 geekCard 数据',
                }

        # 基础筛选
        passed, reason = screen_by_education(resume_data, rules)

        if not passed:
            return {
                'name': name,
                'source': source,
                'screen_result': 'FAIL',
                'score': 0.0,
                'resume_data': resume_data,
                'exclude_reason': reason,
            }

        # 业务规则评分
        score = score_business_rules(resume_data, rules)

        return {
            'name': name,
            'source': source,
            'screen_result': 'PASS',
            'score': score,
            'resume_data': resume_data,
        }

    except Exception as e:
        logger.error(f"筛选 {name} ({source}) 时出错: {e}", exc_info=True)
        return {
            'name': name,
            'source': source,
            'screen_result': 'UNCERTAIN',
            'score': 0.0,
            'resume_data': {},
            'exclude_reason': f'处理错误: {str(e)}',
        }
