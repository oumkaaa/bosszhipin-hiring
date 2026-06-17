"""Command-line entry point for boss-hr-recruiter."""

import sys
import asyncio

from .main import main as run_main


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法：python -m boss_hr_recruiter <runtime_dir> [--phase {1,2,3}]")
        print("\n示例：")
        print("  # 运行完整流程（Phase 1-3）")
        print("  python -m boss_hr_recruiter D:/boss-hiring-runtime/ai-pm-intern")
        print("\n  # 只运行 Phase 1（筛选+打招呼）")
        print("  python -m boss_hr_recruiter D:/boss-hiring-runtime/ai-pm-intern --phase 1")
        print("\n  # 只运行 Phase 2（判断回复）")
        print("  python -m boss_hr_recruiter D:/boss-hiring-runtime/ai-pm-intern --phase 2")
        print("\n  # 只运行 Phase 3（简历处理）")
        print("  python -m boss_hr_recruiter D:/boss-hiring-runtime/ai-pm-intern --phase 3")
        sys.exit(1)

    runtime_dir = sys.argv[1]
    phase = None

    # 解析 --phase 参数
    if len(sys.argv) > 3 and sys.argv[2] == '--phase':
        phase = int(sys.argv[3])
        if phase not in (1, 2, 3):
            print("❌ --phase 参数只能是 1、2 或 3")
            sys.exit(1)

    try:
        asyncio.run(run_main(runtime_dir, phase=phase))
    except KeyboardInterrupt:
        print("\n⚠️ 运行被中断（Ctrl+C）")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 运行失败: {e}")
        sys.exit(1)
