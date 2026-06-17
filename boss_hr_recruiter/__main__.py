"""Command-line entry point for boss-hr-recruiter."""

import sys
import asyncio
import argparse

from .main import main as run_main


def main():
    parser = argparse.ArgumentParser(
        prog="python -m boss_hr_recruiter",
        description="Boss Zhipin Hiring Assistant - Automated recruiter workflow"
    )
    parser.add_argument(
        "runtime_dir",
        help="Runtime directory path"
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3],
        default=None,
        help="Run specific phase (1=screening+greeting, 2=reply judgment, 3=resume handling). Default: all phases"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Simulate without sending real messages"
    )

    args = parser.parse_args()

    try:
        asyncio.run(run_main(args.runtime_dir, phase=args.phase, dry_run=args.dry_run))
    except KeyboardInterrupt:
        print("\nInterrupted by user (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
