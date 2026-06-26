"""
orchestrator/scheduler.py — 调度执行器
=========================================
被 cron 每5分钟唤醒一次，执行轻量任务。

能力注册表（可扩展）：
  crawl_web   → 爬网页/调API（无LLM）
  run_code    → 执行 Python 脚本
  query_kb    → 搜索知识库
  need_think  → 等我处理（调度器跳过）
"""

import io
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 确保能导入同级模块
sys.path.insert(0, str(Path(__file__).parent))

from task_queue import TaskQueue


# ══════════════════════════════════════════════════════════════
# 能力执行器
# ══════════════════════════════════════════════════════════════

def execute_web_crawl(params: dict) -> str:
    url = params.get("url", "")
    if not url:
        return "缺少 url 参数"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Orchestrator/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8", errors="replace")
        return data[:2000]
    except Exception as e:
        return f"爬取失败: {e}"


def execute_run_code(params: dict) -> str:
    code = params.get("code", "")
    script = params.get("script", "")
    if script:
        sp = Path(script)
        if not sp.exists():
            return f"脚本不存在: {script}"
        result = subprocess.run(
            [sys.executable, str(sp)],
            capture_output=True, text=True, timeout=30
        )
    elif code:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=30
        )
    else:
        return "缺少 code 或 script 参数"

    if result.returncode != 0:
        return f"执行失败:\n{result.stderr[:1000]}"
    out = result.stdout.strip()
    return out[:2000] if out else "执行成功（无输出）"


def execute_query_kb(params: dict) -> str:
    query = params.get("query", "")
    if not query:
        return "缺少 query 参数"
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from unified_kb.kb_core import UnifiedKB
        kb = UnifiedKB()
        results = kb.search(query, n_results=5)
        if not results:
            return "未找到相关内容"
        lines = []
        for r in results:
            text = r.get("text", "")[:200]
            score = r.get("score", 0)
            lines.append(f"[{score:.2f}] {text}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"知识库查询失败: {e}"


# 能力注册表
CAPABILITIES = {
    "crawl_web": execute_web_crawl,
    "run_code": execute_run_code,
    "query_kb": execute_query_kb,
}


def run():
    print("[Scheduler] 启动...", flush=True)
    q = TaskQueue()
    tasks = q.pending()

    if not tasks:
        print("[Scheduler] 无待处理任务", flush=True)
        return

    print(f"[Scheduler] 发现 {len(tasks)} 个待处理任务", flush=True)

    for task in tasks:
        if task["need_me"]:
            print(f"  => {task['id']} ({task['type']}): 需要小云处理，跳过", flush=True)
            continue

        handler = CAPABILITIES.get(task["type"])
        if not handler:
            print(f"  => {task['id']} ({task['type']}): 未知任务类型", flush=True)
            q.mark_failed(task["id"], f"未知任务类型: {task['type']}")
            continue

        print(f"  => 执行 {task['id']} ({task['type']})...", flush=True)
        if not q.mark_running(task["id"]):
            print(f"     已被其他调度器领取，跳过", flush=True)
            continue

        try:
            result = handler(task["params"])
            q.mark_done(task["id"], result)
            print(f"     [OK] 完成 ({len(result)} 字符)", flush=True)
        except Exception as e:
            q.mark_failed(task["id"], str(e))
            print(f"     [ERR] 失败: {e}", flush=True)

    print("[Scheduler] 完成", flush=True)


if __name__ == "__main__":
    run()
