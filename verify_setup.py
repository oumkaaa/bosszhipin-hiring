#!/usr/bin/env python3
"""Preflight checks for boss-hr-recruiter skill."""

import sys
import subprocess
from pathlib import Path
from packaging import version


def check_python_version():
    """Check Python version >= 3.10."""
    print("\n[1/7] Checking Python version...")
    py_ver = version.parse(f"{sys.version_info.major}.{sys.version_info.minor}")
    required = version.parse("3.10")

    if py_ver >= required:
        print(f"  [OK] Python {py_ver} >= {required}")
        return True
    else:
        print(f"  [FAIL] Python {py_ver} < {required} required")
        return False


def check_boss_agent_cli():
    """Check boss-agent-cli installation."""
    print("\n[2/7] Checking boss-agent-cli...")
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import boss_agent_cli; print(boss_agent_cli.__version__)"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            ver = result.stdout.strip()
            print(f"  [OK] boss-agent-cli {ver}")
            return True
        else:
            print(f"  [FAIL] boss-agent-cli not found or import failed")
            return False
    except Exception as e:
        print(f"  [FAIL] Error checking boss-agent-cli: {e}")
        return False


def check_project_files():
    """Check required project files exist."""
    print("\n[3/7] Checking project structure...")
    project_dir = Path(__file__).parent
    required_files = [
        "SKILL.md",
        "README.md",
        "requirements.txt",
        "boss_hr_recruiter/__init__.py",
        "boss_hr_recruiter/main.py",
        "boss_hr_recruiter/__main__.py",
        "boss_hr_recruiter/phase1/screening.py",
        "boss_hr_recruiter/phase2/reply_parser.py",
        "boss_hr_recruiter/phase3/goal_judge.py",
        "boss_hr_recruiter/utils/config.py",
        "boss_hr_recruiter/utils/storage.py",
    ]

    missing = []
    for file_path in required_files:
        full_path = project_dir / file_path
        if not full_path.exists():
            missing.append(file_path)

    if missing:
        print(f"  [FAIL] Missing {len(missing)} files:")
        for f in missing:
            print(f"    - {f}")
        return False
    else:
        print(f"  [OK] All {len(required_files)} required files present")
        return True


def check_imports():
    """Check module imports."""
    print("\n[4/7] Checking imports...")
    try:
        from boss_hr_recruiter.main import main
        from boss_hr_recruiter.phase1.screening import screen_and_rate
        from boss_hr_recruiter.utils import load_config
        print("  [OK] All imports successful")
        return True
    except ImportError as e:
        print(f"  [FAIL] Import failed: {e}")
        return False


def check_function_signatures():
    """Check that function signatures match their usage."""
    print("\n[5/7] Checking function signatures...")
    try:
        import inspect
        from boss_hr_recruiter.phase1.screening import screen_and_rate

        sig = inspect.signature(screen_and_rate)
        params = list(sig.parameters.keys())

        expected = ['candidate', 'client', 'config', 'rules', 'logger']
        missing_params = [p for p in expected if p not in params]

        if missing_params:
            print(f"  [FAIL] screen_and_rate missing params: {missing_params}")
            return False
        else:
            print(f"  [OK] screen_and_rate signature correct")
            return True
    except Exception as e:
        print(f"  [FAIL] Signature check failed: {e}")
        return False


def check_no_pycache():
    """Check that __pycache__ is not in distributed code."""
    print("\n[6/7] Checking for __pycache__...")
    project_dir = Path(__file__).parent
    pycache_dirs = list(project_dir.glob("**/__pycache__"))

    if pycache_dirs:
        print(f"  [WARN] Found {len(pycache_dirs)} __pycache__ directories")
        for d in pycache_dirs[:3]:
            print(f"    - {d.relative_to(project_dir)}")
        return False
    else:
        print("  [OK] No __pycache__ found")
        return True


def check_cli_help():
    """Check that CLI help works."""
    print("\n[7/7] Checking CLI help...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "boss_hr_recruiter", "--help"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and "--phase" in result.stdout:
            print("  [OK] CLI help available")
            return True
        else:
            print(f"  [FAIL] CLI help failed")
            return False
    except Exception as e:
        print(f"  [FAIL] Error checking CLI: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("Boss Zhipin Hiring Assistant - Preflight Check")
    print("=" * 60)

    checks = [
        ("Python version", check_python_version()),
        ("boss-agent-cli", check_boss_agent_cli()),
        ("Project files", check_project_files()),
        ("Module imports", check_imports()),
        ("Function signatures", check_function_signatures()),
        ("No __pycache__", check_no_pycache()),
        ("CLI help", check_cli_help()),
    ]

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(1 for _, result in checks if result)
    total = len(checks)

    for name, result in checks:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")

    print("=" * 60)

    if passed == total:
        print(f"\n[OK] All {total} checks passed - ready to run")
        print("\nQuick start:")
        print("  python -m boss_hr_recruiter /path/to/runtime_dir")
        print("  python -m boss_hr_recruiter /path/to/runtime_dir --phase 1 --dry-run")
        return 0
    else:
        print(f"\n[FAIL] {total - passed}/{total} checks failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
