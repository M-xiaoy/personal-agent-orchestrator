"""
orchestrator/dispatch.py — 调度接口（我用来创建任务、查状态）
===============================================================
用法:
    from dispatch import dispatch, check, summary, run_agent

    # 轻量任务（调度器自动执行）
    tid = dispatch("crawl_web", {"url": "..."})
    tid = dispatch("run_code", {"code": "print(1+1)"})
    tid = dispatch("query_kb", {"query": "Smolagents"})

    # Agent 任务（自动选择框架）
    tid = dispatch("agent_task", {
        "task": "对比 Smolagents 和 CrewAI",
        "task_type": "analyze",
        "model": "local",
    })

    # 直接运行 Agent（不等调度器，立即执行）
    result = run_agent("对比 Smolagents 和 CrewAI", task_type="analyze")

    # 查看状态
    check(tid)
    summary()
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from task_queue import TaskQueue

_q = TaskQueue()


def dispatch(task_type: str, params: dict = None,
             need_me: bool = False, notify: bool = True) -> str:
    """创建任务到队列，返回任务ID"""
    return _q.add(task_type, params or {}, need_me=need_me, notify=notify)


def run_agent(task: str, task_type: str = "general",
              model: str = "local", prefer: str = "") -> str:
    """立即用 Agent 框架执行（不走调度器，等结果返回）"""
    from scheduler import execute_agent_task
    return execute_agent_task({
        "task": task,
        "task_type": task_type,
        "model": model,
        "prefer": prefer,
    })


def check(task_id: str) -> dict:
    """查询任务状态和结果"""
    return _q.get(task_id)


def summary() -> str:
    """任务队列概览"""
    stats = _q.count()
    recent = _q.recent(5)

    lines = ["[任务队列状态]"]
    total = sum(stats.values())
    lines.append(f"  总计: {total} 个任务")
    for status, count in sorted(stats.items()):
        lines.append(f"    {status}: {count}")

    if recent:
        lines.append("\n[最近任务]")
        for t in recent:
            status_icon = {"done": "[OK]", "failed": "[ERR]",
                           "running": "[..]", "pending": "[..]"}.get(t["status"], "[?]")
            me = " (需小云)" if t["need_me"] else ""
            lines.append(f"  {status_icon} {t['type']} #{t['id'][:8]}{me}")

    # 显示可用 Agent
    try:
        from agents import list_agents
        agents = list_agents()
        avail = [a["name"] for a in agents if a["available"]]
        if avail:
            lines.append(f"\n[可用 Agent] {' '.join(avail)}")
    except ImportError:
        pass

    return "\n".join(lines)


def pending_for_me() -> list[dict]:
    """获取等我处理的任务"""
    return [t for t in _q.pending() if t["need_me"]]
