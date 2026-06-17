#!/usr/bin/env python3
"""验证boss-hr-recruiter项目结构和文件完整性."""

import sys
import io
from pathlib import Path

# 设置标准输出为UTF-8（处理GBK编码问题）
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def verify_project_structure():
    """验证项目结构."""
    project_dir = Path(__file__).parent
    required_files = [
        "SKILL.md",
        "README.md",
        ".env.example",
        "requirements.txt",
        "boss_hr_recruiter/__init__.py",
        "boss_hr_recruiter/main.py",
        "boss_hr_recruiter/phase1/__init__.py",
        "boss_hr_recruiter/phase1/models.py",
        "boss_hr_recruiter/phase1/screening.py",
        "boss_hr_recruiter/phase2/__init__.py",
        "boss_hr_recruiter/phase2/reply_parser.py",
        "boss_hr_recruiter/phase3/__init__.py",
        "boss_hr_recruiter/phase3/goal_judge.py",
        "boss_hr_recruiter/utils/__init__.py",
        "boss_hr_recruiter/utils/errors.py",
        "boss_hr_recruiter/utils/config.py",
        "boss_hr_recruiter/utils/logger.py",
        "boss_hr_recruiter/utils/auth.py",
        "boss_hr_recruiter/utils/storage.py",
        "docs/MIGRATION.md",
        "docs/TROUBLESHOOTING.md",
    ]

    print("=" * 60)
    print("Boss直聘招聘助手 - 项目验证")
    print("=" * 60)

    missing_files = []
    for file in required_files:
        file_path = project_dir / file
        if file_path.exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - MISSING")
            missing_files.append(file)

    print("=" * 60)

    if missing_files:
        print(f"\n❌ 发现 {len(missing_files)} 个缺失文件：")
        for f in missing_files:
            print(f"  - {f}")
        return False
    else:
        print("\n✅ 所有文件都已创建！")
        return True


def verify_imports():
    """验证导入是否正常."""
    print("\n验证模块导入...")

    try:
        from boss_hr_recruiter import main
        print("✅ boss_hr_recruiter.main")
    except ImportError as e:
        print(f"❌ boss_hr_recruiter.main: {e}")
        return False

    try:
        from boss_hr_recruiter.utils import (
            SkillLogger,
            CandidateStorage,
            load_config,
            CookieExpiredError,
        )
        print("✅ boss_hr_recruiter.utils")
    except ImportError as e:
        print(f"❌ boss_hr_recruiter.utils: {e}")
        return False

    try:
        from boss_hr_recruiter.phase1.screening import screen_and_rate
        print("✅ boss_hr_recruiter.phase1.screening")
    except ImportError as e:
        print(f"❌ boss_hr_recruiter.phase1.screening: {e}")
        return False

    try:
        from boss_hr_recruiter.phase2.reply_parser import parse_reply_text
        print("✅ boss_hr_recruiter.phase2.reply_parser")
    except ImportError as e:
        print(f"❌ boss_hr_recruiter.phase2.reply_parser: {e}")
        return False

    try:
        from boss_hr_recruiter.phase3.goal_judge import judge_goal_completion
        print("✅ boss_hr_recruiter.phase3.goal_judge")
    except ImportError as e:
        print(f"❌ boss_hr_recruiter.phase3.goal_judge: {e}")
        return False

    print("✅ 所有模块导入正常")
    return True


def main():
    """主函数."""
    # 验证项目结构
    structure_ok = verify_project_structure()

    # 验证导入
    imports_ok = verify_imports()

    print("\n" + "=" * 60)
    if structure_ok and imports_ok:
        print("✅ 验证通过！项目已准备就绪")
        print("\n快速开始：")
        print("  1. pip install -r requirements.txt")
        print("  2. boss login")
        print("  3. python -m boss_hr_recruiter.main /path/to/runtime_dir")
        print("=" * 60)
        return 0
    else:
        print("❌ 验证失败！请检查上述错误")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
