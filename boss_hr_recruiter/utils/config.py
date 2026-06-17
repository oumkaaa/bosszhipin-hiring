"""Configuration loading for boss-hr-recruiter skill."""

import json
import os
from pathlib import Path
from typing import Any, Dict

from .errors import ConfigError


def _ensure_encoding():
    """自动设置UTF-8编码（Windows兼容）."""
    if os.name == 'nt' and os.environ.get('PYTHONIOENCODING') != 'utf-8':
        os.environ['PYTHONIOENCODING'] = 'utf-8'


def load_config(runtime_dir: str) -> Dict[str, Any]:
    """加载运行时配置文件."""
    # 确保编码设置
    _ensure_encoding()

    # 规范化路径（跨平台兼容）
    runtime_path = Path(runtime_dir).resolve()

    if not runtime_path.exists():
        raise ConfigError(f"运行时目录不存在: {runtime_dir}")

    # 自动创建logs目录
    logs_dir = runtime_path / "logs"
    logs_dir.mkdir(exist_ok=True)

    # 加载run-context.json
    context_file = runtime_path / "run-context.json"
    if not context_file.exists():
        raise ConfigError(f"run-context.json 不存在: {context_file}")

    with open(context_file, 'r', encoding='utf-8') as f:
        context = json.load(f)

    # 加载screen-rules.json
    rules_file = runtime_path / "screen-rules.json"
    rules = {}
    if rules_file.exists():
        with open(rules_file, 'r', encoding='utf-8') as f:
            rules = json.load(f)

    # 合并配置
    config = {
        **context,
        'runtime_dir': runtime_dir,
        'screen_rules': rules,
    }

    return config


def load_candidates(runtime_dir: str) -> list:
    """加载候选人列表."""
    candidates_file = Path(runtime_dir) / "candidates.json"

    if not candidates_file.exists():
        return []

    with open(candidates_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get('candidates', [])


def save_candidates(runtime_dir: str, candidates: list) -> None:
    """保存候选人列表（原子写入）."""
    candidates_file = Path(runtime_dir) / "candidates.json"
    tmp_file = Path(runtime_dir) / "candidates.json.tmp"

    # 写入临时文件
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump({
            'version': 'boss-hiring-v2',
            'candidates': candidates
        }, f, ensure_ascii=False, indent=2)
        f.write('\n')

    # 原子替换
    tmp_file.replace(candidates_file)
