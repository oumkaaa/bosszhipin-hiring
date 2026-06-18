#!/bin/bash
# Boss Zhipin Hiring Assistant - Linux/macOS startup script
# Usage: bash run.sh /path/to/runtime_dir [--live]

RUNTIME_DIR="${1:-.}"
LIVE_FLAG=""
if [ "${2:-}" = "--live" ]; then
    LIVE_FLAG="--live"
fi
export PYTHONIOENCODING=utf-8

if [ ! -d "$RUNTIME_DIR" ]; then
    echo "Runtime directory does not exist: $RUNTIME_DIR" >&2
    exit 1
fi

echo "============================================================"
echo "Boss Zhipin Hiring Assistant - Starting"
echo "============================================================"
echo "Runtime directory: $RUNTIME_DIR"
if [ -n "$LIVE_FLAG" ]; then
    echo "Mode: LIVE"
else
    echo "Mode: DRY-RUN"
fi
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python -m boss_hr_recruiter "$RUNTIME_DIR" $LIVE_FLAG
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "Completed successfully"
else
    echo ""
    echo "Failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE
