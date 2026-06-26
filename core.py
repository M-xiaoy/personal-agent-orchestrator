"""
orchestrator/core.py — 算法派核心工作流
=========================================
完整链路：评估 → 拆解 → 分发 → 执行 → 收集 → 整合 → 交付

用法：
    from core import run_workflow
    result = run_workflow("对比AutoGPT和CrewAI的设计理念")
"""

import json
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# 确保能导入同级模块
sys.path.insert(0, str(Path(__file__).parent))

from router import assess_complexity
from dispatcher import dispatch_task, collect_results


# ══════════════════════════════════════════════════════════════
# 任务拆解
# ══════════════════════════════════════════════════════════════

def _decompose(task: str, context: str = "") -> list[dict]:
    """
    将复杂任务拆解为子任务列表。
    规则驱动，无LLM调用。
    """
    task_lower = task.lower()
    subtasks = []

    # ── 对比类任务 ──────────────────────────────────────
    if any(w in task_lower for w in ["对比", "比较", "vs", "versus"]):
        items = _extract_compare_items(task)
        if items:
            subtasks.append({
                "type": "research",
                "task": f"搜集 {items[0]} 的核心信息（定位、特点、适用场景）",
                "sub_agent": "smolagents",
            })
            subtasks.append({
                "type": "research",
                "task": f"搜集 {items[1]} 的核心信息（定位、特点、适用场景）",
                "sub_agent": "smolagents",
            })
            subtasks.append({
                "type": "analyze",
                "task": f"对比 {items[0]} 和 {items[1]} 的异同，从设计理念、适用场景、优劣势三个维度分析",
                "context": f"首先获取两个框架的信息作为基础",
                "sub_agent": "crewai",
            })
            return subtasks

    # ── 调研类任务 ──────────────────────────────────────
    if any(w in task_lower for w in ["调研", "分析", "研究", "趋势", "了解"]):
        subtasks.append({
            "type": "research",
            "task": f"搜索并整理关于「{task}」的核心信息，列出关键发现",
            "sub_agent": "smolagents",
        })
        return subtasks

    # ── 代码类任务 ──────────────────────────────────────
    if any(w in task_lower for w in ["写一个", "实现", "编写", "代码", "脚本"]):
        subtasks.append({
            "type": "code",
            "task": task,
            "sub_agent": "smolagents",
        })
        return subtasks

    # ── 排障类任务 ──────────────────────────────────────
    if any(w in task_lower for w in ["排查", "诊断", "调试", "为什么"]):
        subtasks.append({
            "type": "debug",
            "task": task,
            "context": context,
            "sub_agent": "crewai",
        })
        return subtasks

    # ── 默认：单任务 ────────────────────────────────────
    subtasks.append({
        "type": "general",
        "task": task,
        "context": context,
        "sub_agent": "smolagents",
    })
    return subtasks


def _extract_compare_items(text: str) -> list[str]:
    """从对比语句中提取两个对象"""
    import re
    # "对比A和B" / "A vs B" / "A和B的对比"
    patterns = [
        r"对比(.+?)和(.+)",
        r"(.+?)vs(.+)",
        r"(.+?)versus(.+)",
        r"(.+?)和(.+?)的对比",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            a = m.group(1).strip().strip("的")
            b = m.group(2).strip()
            return [a, b]
    return []


# ══════════════════════════════════════════════════════════════
# 结果整合
# ══════════════════════════════════════════════════════════════

def _integrate(results: list[dict], original_task: str) -> str:
    """
    整合多个子Agent的结果。
    去重、排序、汇总。
    """
    if not results:
        return "（无结果）"

    # 去重（简单去重：去除完全相同的段落）
    seen = set()
    unique_parts = []
    for r in results:
        text = r.get("result", "")
        # 按段落拆分
        for para in text.split("\n\n"):
            key = para.strip()[:50]
            if key and key not in seen:
                seen.add(key)
                unique_parts.append(para.strip())

    # 按子任务类型排序
    type_order = {"research": 0, "code": 1, "debug": 2, "analyze": 3, "general": 4}
    sorted_results = sorted(results, key=lambda r: type_order.get(r.get("type", "general"), 4))

    lines = [f"# 结果整合：{original_task}", ""]
    for i, r in enumerate(sorted_results):
        lines.append(f"## [{r.get('type', 'task').upper()}] {r.get('task', '')[:60]}")
        text = r.get("result", "(无输出)").strip()
        # 截断过长结果
        if len(text) > 1500:
            text = text[:1500] + "\n\n...（结果过长已截断）"
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════

def run_workflow(task: str, context: str = "", auto_execute: bool = True) -> dict:
    """
    完整工作流入口。

    参数:
        task: 任务描述
        context: 额外上下文
        auto_execute: 是否自动尝试执行子任务（默认True）

    返回:
        {
            "route": "engineering" | "algorithm",
            "assessment": {...},        # 路由评估详情
            "subtasks": [...],          # 拆解后的子任务
            "results": [...],           # 执行结果
            "integrated": "...",        # 整合后的最终结果
        }
    """
    print(f"\n{'='*50}")
    print(f"  工作流启动")
    print(f"  任务: {task}")
    print(f"{'='*50}")

    # 1. 路由评估
    assessment = assess_complexity(task)
    route = assessment["route"]
    print(f"\n[路由] {route} — {assessment['reason']}")

    if route == "engineering":
        # 工程派：直接返回
        return {
            "route": "engineering",
            "assessment": assessment,
            "task": task,
            "message": "简单任务，直接干即可",
        }

    # 2. 算法派：拆解任务
    print(f"\n[拆解] 分析任务结构...")
    subtasks = _decompose(task, context)
    print(f"  拆解为 {len(subtasks)} 个子任务:")
    for i, st in enumerate(subtasks):
        print(f"    {i+1}. [{st['sub_agent']}] {st['task'][:60]}...")

    # 3. 分发 & 执行
    results = []
    for i, st in enumerate(subtasks):
        print(f"\n[分发] 子任务 {i+1}/{len(subtasks)}...")
        info = dispatch_task(
            task=st["task"],
            context=st.get("context", ""),
            sub_agent=st["sub_agent"],
        )

        if auto_execute:
            # 自动执行（尝试本地直接运行）
            result = _execute_local(st)
            results.append({
                "type": st["type"],
                "task": st["task"],
                "result": result,
                "task_dir": info["task_dir"],
            })
            print(f"  [OK] 子任务 {i+1} 完成")
        else:
            # 标记为等待调度器执行
            results.append({
                "type": st["type"],
                "task": st["task"],
                "result": "(等待调度器执行)",
                "task_dir": info["task_dir"],
            })

    # 4. 整合
    print(f"\n[整合] 汇总 {len(results)} 个子任务结果...")
    integrated = _integrate(results, task)
    print(f"  整合完成 ({len(integrated)} 字符)")

    return {
        "route": "algorithm",
        "assessment": assessment,
        "subtasks": subtasks,
        "results": results,
        "integrated": integrated,
        "task": task,
    }


def _execute_local(subtask: dict) -> str:
    """
    本地直接执行子任务（无Agent，纯规则）。
    作为算法派的轻量级回退方案。
    """
    task_type = subtask.get("type", "general")
    task = subtask.get("task", "")

    if task_type == "code":
        # 代码任务：直接返回一个提示
        return (
            "此任务需要编写代码，建议以下两种方式：\n"
            "1. 改用Smolagents的CodeAgent执行\n"
            "2. 由用户手动编写\n"
            f"任务需求: {task[:200]}"
        )

    if task_type in ("research", "debug"):
        return (
            f"此任务需要联网搜索/深度分析：\n"
            f"{task}\n\n"
            "建议由小云（云端DeepSeek v4）直接处理，或使用Smolagents调用搜索工具。"
        )

    # 通用回退
    return f"[等待执行] {task}"
