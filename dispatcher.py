"""
orchestrator/dispatcher.py — 文件即接口：任务分配与结果收集
==============================================================
用法：
    from dispatcher import dispatch_task, collect_results

    # 创建任务文件，派给子Agent
    task_info = dispatch_task("对比AutoGPT和CrewAI", sub_agent="crewai")

    # 子Agent完成后来收结果
    result = collect_results(task_info["task_dir"])
"""

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# 任务目录
TASKS_DIR = Path(__file__).parent / "tasks"
TASKS_DIR.mkdir(exist_ok=True)


def dispatch_task(
    task: str,
    context: str = "",
    sub_agent: str = "auto",
    model: str = "local",
    timeout_minutes: int = 10,
) -> dict:
    """
    创建任务文件，返回任务信息。

    sub_agent: "auto" | "smolagents" | "crewai" | "agno" | "script"
    model: "local" | "cloud" | "auto"
    """
    task_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_dir = TASKS_DIR / f"task_{timestamp}_{task_id}"
    task_dir.mkdir(parents=True, exist_ok=True)

    # 写任务文件
    task_file = task_dir / "TASK.md"
    content = _format_task(task, context, sub_agent, model)
    task_file.write_text(content, encoding="utf-8")

    # 写状态文件（标记为等待执行）
    status = {
        "id": task_id,
        "status": "pending",
        "sub_agent": sub_agent,
        "model": model,
        "created_at": timestamp,
        "timeout_minutes": timeout_minutes,
    }
    (task_dir / "status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "task_id": task_id,
        "task_dir": str(task_dir),
        "task_file": str(task_file),
        "status_file": str(task_dir / "status.json"),
        "result_file": str(task_dir / "RESULT.md"),
        "sub_agent": sub_agent,
    }


def collect_results(task_dir: str, timeout_seconds: int = 600) -> dict:
    """
    等待并收集结果。
    返回: { "status": "done"|"timeout"|"error", "result": "...", "error": "..." }
    """
    task_path = Path(task_dir)
    result_file = task_path / "RESULT.md"
    status_file = task_path / "status.json"

    start = time.time()
    while time.time() - start < timeout_seconds:
        # 检查结果文件
        if result_file.exists():
            result_text = result_file.read_text(encoding="utf-8")
            # 更新状态
            _update_status(status_file, "done")
            return {"status": "done", "result": result_text, "task_dir": task_dir}

        # 检查状态
        if status_file.exists():
            status = json.loads(status_file.read_text(encoding="utf-8"))
            if status.get("status") == "failed":
                return {
                    "status": "failed",
                    "error": status.get("error", "未知错误"),
                    "task_dir": task_dir,
                }

        time.sleep(2)

    _update_status(status_file, "timeout")
    return {"status": "timeout", "error": "等待超时", "task_dir": task_dir}


def dispatch_and_execute(
    task: str,
    context: str = "",
    sub_agent: str = "auto",
    model: str = "local",
) -> dict:
    """
    创建任务 + 立即执行（不走调度器等待）。
    自动根据任务类型选择合适的 Agent 框架。
    """
    # 先创建任务文件
    info = dispatch_task(task, context, sub_agent, model)
    task_dir = Path(info["task_dir"])

    # 推断 task_type
    task_lower = task.lower()
    if any(w in task_lower for w in ["代码", "写一个", "实现", "编写", "脚本", "def ", "class "]):
        task_type = "code"
    elif any(w in task_lower for w in ["对比", "比较", "vs", "分析", "评估"]):
        task_type = "analyze"
    elif any(w in task_lower for w in ["搜索", "调研", "查一下"]):
        task_type = "research"
    else:
        task_type = "general"

    # 选 Agent
    try:
        from agents import get_agent_for_task
        agent = get_agent_for_task(task_type, prefer=sub_agent if sub_agent != "auto" else "")
        if not agent:
            _update_status(task_dir / "status.json", "failed", "无可用 Agent")
            info["status"] = "failed"
            info["error"] = "无可用 Agent 框架"
            return info

        result = agent.run(task, context=context, model=model)
        (task_dir / "RESULT.md").write_text(str(result), encoding="utf-8")
        _update_status(task_dir / "status.json", "done")
        info["status"] = "done"
        info["result"] = result
        info["agent_used"] = agent.name
    except Exception as e:
        _update_status(task_dir / "status.json", "failed", str(e))
        info["status"] = "failed"
        info["error"] = str(e)

    return info


def list_pending_tasks() -> list:
    """列出所有待处理的任务"""
    results = []
    for d in sorted(TASKS_DIR.iterdir()):
        if not d.is_dir():
            continue
        status_file = d / "status.json"
        if not status_file.exists():
            continue
        status = json.loads(status_file.read_text(encoding="utf-8"))
        if status.get("status") == "pending":
            task_file = d / "TASK.md"
            task_text = task_file.read_text(encoding="utf-8")[:300] if task_file.exists() else ""
            results.append({
                "task_dir": str(d),
                "task_id": status.get("id", ""),
                "sub_agent": status.get("sub_agent", ""),
                "preview": task_text[:100],
            })
    return results


# ── 内部辅助 ──────────────────────────────────────────────

def _format_task(task: str, context: str, sub_agent: str, model: str) -> str:
    return f"""# Agent 任务

## 任务描述
{task}

## 上下文
{context or "（无额外上下文）"}

## 要求
- 输出结果写到同目录的 RESULT.md
- 保持简洁，只说结论
- 如果需要更多信息，在 RESULT.md 中说明

## 配置
- 执行框架: {sub_agent}
- 模型偏好: {model}
- 创建时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""


def _update_status(status_file: Path, new_status: str, error: str = ""):
    if not status_file.exists():
        return
    try:
        status = json.loads(status_file.read_text(encoding="utf-8"))
        status["status"] = new_status
        if error:
            status["error"] = error
        status_file.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
