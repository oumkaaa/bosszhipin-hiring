#!/bin/bash
# Boss直聘招聘助手 - Linux/macOS启动脚本
# 用法: bash run.sh /path/to/runtime_dir

RUNTIME_DIR="${1:-.}"

# 设置UTF-8编码（解决编码问题）
export PYTHONIOENCODING=utf-8

# 验证运行时目录
if [ ! -d "$RUNTIME_DIR" ]; then
    echo "✗ 运行时目录不存在: $RUNTIME_DIR"
    exit 1
fi

echo "============================================================"
echo "Boss直聘招聘助手启动"
echo "============================================================"
echo "运行时目录: $RUNTIME_DIR"
echo ""

# 进入脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 运行主程序
python -m boss_hr_recruiter.main "$RUNTIME_DIR"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ 执行完成"
else
    echo ""
    echo "✗ 执行失败 (退出码: $EXIT_CODE)"
fi

exit $EXIT_CODE
