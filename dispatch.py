"""
orchestrator/dispatch.py — 小云的调度接口
============================================
我在聊天中用这个模块创建任务、检查状态。
用法（在我的上下文中）：
    from orchestrator.dispatch import dispatch, check, summary
    tid = dispatch("crawl_web", {"url": "..."})
    check(tid)  # 获取结果
    summary()   # 查看所有任务状态
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from task_queue import TaskQueue

_q = TaskQueue()


def dispatch(task_type: str, params: dict = None,
             need_me: bool = False, notify: bool = True) -> str:
    """创建一个任务，返回任务ID"""
    return _q.add(task_type, params or {}, need_me=need_me, notify=notify)


def check(task_id: str) -> dict:
    """查询任务状态和结果"""
    return _q.get(task_id)


def summary() -> str:
    """任务概览"""
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

    return "\n".join(lines)


def pending_for_me() -> list[dict]:
    """获取等我处理的任务"""
    return [t for t in _q.pending() if t["need_me"]]
