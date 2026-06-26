"""Agent 框架追踪器 — 设置每日自动运行"""
import io
import os
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RUN_SCRIPT = os.path.join(SCRIPT_DIR, "run.py")
PYTHON = sys.executable


def setup_scheduler():
    task_name = "AgentTrackerDaily"
    cmd = f'"{PYTHON}" "{RUN_SCRIPT}"'

    subprocess.run(
        f'schtasks /Delete /TN "{task_name}" /F',
        shell=True, capture_output=True
    )

    result = subprocess.run(
        f'schtasks /Create /SC DAILY /TN "{task_name}" '
        f'/TR "{cmd}" /ST 09:00 /RL HIGHEST /F',
        shell=True, capture_output=True, text=True,
    )

    if result.returncode == 0:
        print(f"[OK] 定时任务已创建: {task_name}")
        print(f"     每天 09:00 自动运行")
        print(f"     脚本: {RUN_SCRIPT}")
    else:
        print(f"[ERR] 创建失败: {result.stderr}")
        print(f"     提示: 以管理员身份运行, 或手动执行:")
        print(f"     {cmd}")


def remove_scheduler():
    task_name = "AgentTrackerDaily"
    subprocess.run(
        f'schtasks /Delete /TN "{task_name}" /F',
        shell=True
    )
    print(f"[DEL] 已删除定时任务: {task_name}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--remove":
        remove_scheduler()
    else:
        setup_scheduler()
