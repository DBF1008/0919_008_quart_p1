#!/usr/bin/env bash
# 手动单元测试脚本
# 覆盖本次异步任务生命周期修复的三个文件：
#   - src/quart/utils.py  (cancel_tasks / raise_task_exceptions)
#   - src/quart/asgi.py   (HTTP / WebSocket 连接的异常传播)
#   - src/quart/app.py    (background_tasks 清理与 shutdown)
#
# 用法:
#   ./test.sh            # 运行与本次修复相关的单元测试 + 全量回归
#   ./test.sh targeted   # 只运行与本次修复相关的单元测试
#   ./test.sh full       # 只运行全量回归
set -euo pipefail

cd "$(dirname "$0")"

MODE="${1:-all}"

# ---------- 1. 准备虚拟环境 ----------
if [ ! -x .venv/bin/python ]; then
    if command -v uv >/dev/null 2>&1; then
        echo ">>> uv sync (tests group)"
        uv sync --frozen --no-default-groups --group tests
    else
        echo ">>> python3 -m venv .venv"
        python3 -m venv .venv
        .venv/bin/pip install -e . \
            pytest pytest-asyncio pytest-cov pytest-sugar python-dotenv
    fi
fi

PYTEST=.venv/bin/pytest

# ---------- 2. 与本次修复直接相关的单元测试 ----------
run_targeted() {
    echo ">>> [1/4] utils: cancel_tasks / raise_task_exceptions"
    "$PYTEST" tests/test_utils.py -v

    echo ">>> [2/4] asgi: HTTP/WebSocket 异常传播一致性"
    "$PYTEST" tests/test_asgi.py -v

    echo ">>> [3/4] app: background_tasks 生命周期"
    "$PYTEST" tests/test_background_tasks.py -v

    echo ">>> [4/4] app 相关回归"
    "$PYTEST" tests/test_app.py -v
}

# ---------- 3. 全量回归 ----------
run_full() {
    echo ">>> 全量单元测试"
    "$PYTEST" tests/
}

case "$MODE" in
    targeted) run_targeted ;;
    full)     run_full ;;
    all)      run_targeted; run_full ;;
    *) echo "未知模式: $MODE (可选: targeted | full | all)" >&2; exit 2 ;;
esac

echo ">>> 全部通过 ✅"
