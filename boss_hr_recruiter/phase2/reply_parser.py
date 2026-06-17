"""Reply parsing for Phase 2."""

import re
from typing import Any, Dict


def parse_reply_text(reply: str, rules: Dict[str, Any]) -> Dict[str, Any]:
    """从候选人回复中解析关键信息.

    Args:
        reply: 候选人回复文本
        rules: 回复规则

    Returns:
        {
            'qualified': True/False,
            'arrival_weeks': int,
            'days_per_week': int,
            'duration_months': int,
            'needs_clarification': bool,
            'missing_fields': list,
            'reason': str,
        }
    """
    result = {
        'qualified': False,
        'arrival_weeks': None,
        'days_per_week': None,
        'duration_months': None,
        'needs_clarification': False,
        'missing_fields': [],
        'reason': '',
    }

    # 获取规则
    max_arrival_weeks = rules.get('max_arrival_weeks', 2)
    min_days_per_week = rules.get('min_days_per_week', 4)
    min_duration_months = rules.get('min_duration_months', 3)

    # 提取到岗时间 - 正则匹配 "X周内", "X个月内", "X天内"等
    arrival_match = re.search(r'(\d+)\s*(?:周|个月|天|星期)(?:内|后)?', reply)
    if arrival_match:
        num = int(arrival_match.group(1))
        if '周' in arrival_match.group(0) or '星期' in arrival_match.group(0):
            result['arrival_weeks'] = num
        elif '天' in arrival_match.group(0):
            result['arrival_weeks'] = max(1, num // 7)
        elif '个月' in arrival_match.group(0):
            result['arrival_weeks'] = num * 4
    else:
        result['missing_fields'].append('arrival_weeks')

    # 提取每周天数
    days_match = re.search(r'(?:一周|每周)\s*(\d+)\s*(?:天|日)', reply)
    if days_match:
        result['days_per_week'] = int(days_match.group(1))
    else:
        # 尝试提取 "5天" "4天"
        days_match = re.search(r'(\d+)\s*天', reply)
        if days_match:
            result['days_per_week'] = int(days_match.group(1))
        else:
            result['missing_fields'].append('days_per_week')

    # 提取实习时长
    duration_match = re.search(r'实习?\s*(\d+)\s*(?:个月|月)', reply)
    if duration_match:
        result['duration_months'] = int(duration_match.group(1))
    else:
        result['missing_fields'].append('duration_months')

    # 判断是否需要澄清
    if result['missing_fields']:
        result['needs_clarification'] = True
        result['reason'] = f"缺少信息：{','.join(result['missing_fields'])}"
        return result

    # 判断是否达标
    if (result['arrival_weeks'] is not None and
        result['arrival_weeks'] <= max_arrival_weeks and
        result['days_per_week'] is not None and
        result['days_per_week'] >= min_days_per_week and
        result['duration_months'] is not None and
        result['duration_months'] >= min_duration_months):
        result['qualified'] = True
    else:
        if result['arrival_weeks'] and result['arrival_weeks'] > max_arrival_weeks:
            result['reason'] = f"到岗时间过长：{result['arrival_weeks']}周（最多{max_arrival_weeks}周）"
        elif result['days_per_week'] and result['days_per_week'] < min_days_per_week:
            result['reason'] = f"每周天数不足：{result['days_per_week']}天（至少{min_days_per_week}天）"
        elif result['duration_months'] and result['duration_months'] < min_duration_months:
            result['reason'] = f"实习时长不足：{result['duration_months']}个月（至少{min_duration_months}个月）"

    return result
