"""
orchestrator/core.py — 算法派核心工作流
=========================================
并行执行 + token按需分配

核心设计：
  - 机械活（爬虫/拉数据/跑代码）→ 子进程本地跑，0 token
  - 推理活（分析/对比/决策）→ 我（云端）处理
  - 整合活（去重/筛选）→ 本地Python规则，0 token

用法：
    from core import run_workflow
    result = run_workflow("对比AutoGPT和CrewAI的设计理念")
"""

import io
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from router import assess_complexity
from task_queue import TaskQueue


# ══════════════════════════════════════════════════════════════
# 缓存：避免重复查询
# ══════════════════════════════════════════════════════════════

_cache = {}  # 进程内缓存


def _cached_fetch(url: str, ttl_seconds: int = 3600) -> str:
    """带缓存的HTTP请求"""
    now = time.time()
    if url in _cache:
        data, ts = _cache[url]
        if now - ts < ttl_seconds:
            return data

    req = urllib.request.Request(url, headers={"User-Agent": "Orchestrator/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read().decode("utf-8", errors="replace")

    _cache[url] = (data, now)
    return data


# ══════════════════════════════════════════════════════════════
# 任务拆解（规则驱动，0 token）
# ══════════════════════════════════════════════════════════════

def _decompose(task: str, context: str = "") -> list[dict]:
    """
    拆解任务，给每个子任务标注：
      - type: research | code | debug | analyze | general
      - cost: "free" | "cloud"    ← 关键：标注是否消耗云端token
    """
    task_lower = task.lower()
    subtasks = []

    # ── 对比类：拆3个，2个free（搜数据）+ 1个cloud（分析） ──
    if any(w in task_lower for w in ["对比", "比较", "vs", "versus"]):
        items = _extract_compare_items(task)
        if items:
            subtasks.append({
                "type": "research",
                "cost": "free",
                "task": f"搜集 {items[0]} 的核心信息（定位、特点、适用场景）",
                "handler": "_fetch_github_info",
                "target": items[0],
            })
            subtasks.append({
                "type": "research",
                "cost": "free",
                "task": f"搜集 {items[1]} 的核心信息（定位、特点、适用场景）",
                "handler": "_fetch_github_info",
                "target": items[1],
            })
            subtasks.append({
                "type": "analyze",
                "cost": "cloud",      # ← 这一步才花钱
                "task": f"基于数据对比 {items[0]} 和 {items[1]} 的异同",
                "handler": "_need_cloud",
            })
            return subtasks

    # ── 搜索/调研类：free ──────────────────────────────────────
    if any(w in task_lower for w in ["搜索", "搜一下", "查一下", "查查", "调研"]):
        subtasks.append({
            "type": "research",
            "cost": "free",
            "task": task,
            "handler": "_web_search",
        })
        return subtasks

    # ── 代码类：free（子进程跑，0 token） ────────────────────────
    if any(w in task_lower for w in ["写一个", "实现", "编写", "代码", "脚本", "demo"]):
        subtasks.append({
            "type": "code",
            "cost": "free",
            "task": task,
            "handler": "_local_code",
        })
        return subtasks

    # ── 排障类：free + cloud ──────────────────────────────────
    if any(w in task_lower for w in ["排查", "诊断", "调试", "为什么"]):
        subtasks.append({
            "type": "debug",
            "cost": "free",        # 先搜已知解决方案
            "task": f"搜索「{task}」的解决方案",
            "handler": "_web_search",
        })
        return subtasks

    # 默认：free
    subtasks.append({
        "type": "general",
        "cost": "free",
        "task": task,
        "handler": "_web_search",
    })
    return subtasks


def _extract_compare_items(text: str) -> list[str]:
    import re
    # 先清除开头无意义词
    cleaned = re.sub(r"^(帮我|请|可以|需要)", "", text).strip()
    patterns = [
        (r"对比[一下]*(.+?)和(.+)", lambda m: (m.group(1), m.group(2))),
        (r"(.+?)vs(.+)", lambda m: (m.group(1), m.group(2))),
        (r"(.+?)versus(.+)", lambda m: (m.group(1), m.group(2))),
        (r"(.+?)和(.+?)的对比", lambda m: (m.group(1), m.group(2))),
    ]
    for pattern, extractor in patterns:
        m = re.search(pattern, cleaned)
        if m:
            a, b = extractor(m)
            # 清理多余尾部
            a = re.sub(r"[，,从的].*$", "", a).strip()
            b = re.sub(r"[，,从的].*$", "", b).strip()
            return [a, b]
    return []


# ══════════════════════════════════════════════════════════════
# 子任务执行器（全是free，0 token）
# ══════════════════════════════════════════════════════════════

def _fetch_github_info(target: str) -> str:
    """搜GitHub信息（免费，调GitHub API）"""
    target = target.strip()
    # 尝试仓库名格式: owner/name
    if "/" in target:
        owner, name = target.split("/", 1)
    else:
        # 搜索可能的仓库名
        search_query = target.replace(" ", "+")
        try:
            data = _cached_fetch(
                f"https://api.github.com/search/repositories?q={search_query}&sort=stars&per_page=3"
            )
            result = json.loads(data)
            items = result.get("items", [])
            if items:
                lines = [f"GitHub 搜索结果：「{target}」", ""]
                for item in items[:3]:
                    lines.append(f"- {item['full_name']}：⭐{item['stargazers_count']:,}")
                    lines.append(f"  {item.get('description', '(无描述)')}")
                    lines.append(f"  语言: {item.get('language', '未知')}")
                return "\n".join(lines)
        except Exception as e:
            return f"[搜索失败] {e}"

    try:
        data = _cached_fetch(f"https://api.github.com/repos/{owner}/{name}")
        repo = json.loads(data)
        return (
            f"仓库: {repo['full_name']}\n"
            f"Stars: ⭐{repo['stargazers_count']:,}\n"
            f"Forks: 🍴{repo['forks_count']:,}\n"
            f"Issues: {repo['open_issues_count']}\n"
            f"语言: {repo.get('language', '未知')}\n"
            f"描述: {repo.get('description', '(无)')}"
        )
    except Exception as e:
        return f"[获取失败] {e}"


def _web_search(params: dict | str = None) -> str:
    """搜索占位（调度时由我处理）"""
    if isinstance(params, str):
        return f"[需搜索] {params}\n（调度器暂不支持web_search，上线后我处理）"
    task = params.get("task", "") if isinstance(params, dict) else str(params)
    return f"[需搜索] {task}\n（调度器暂不支持web_search，上线后我处理）"


def _local_code(params: dict | str = None) -> str:
    """子进程跑代码（免费）"""
    task = params.get("task", "") if isinstance(params, dict) else str(params)
    return (
        f"[需写代码] {task[:200]}\n"
        f"（代码类任务由调度器创建任务文件后执行）"
    )


def _need_cloud(params: dict | str = None) -> str:
    """需要云端模型处理（标记为cloud，调度时由我分析）"""
    task = params.get("task", "") if isinstance(params, dict) else str(params)
    return f"[需云处理] {task}"


# handler 映射
_HANDLERS = {
    "_fetch_github_info": _fetch_github_info,
    "_web_search": _web_search,
    "_local_code": _local_code,
    "_need_cloud": _need_cloud,
}


# ══════════════════════════════════════════════════════════════
# 结果整合（本地规则，0 token）
# ══════════════════════════════════════════════════════════════

def _integrate(results: list[dict], original_task: str) -> str:
    if not results:
        return "（无结果）"

    # 去重
    seen = set()
    unique_parts = []
    for r in results:
        text = r.get("result", "")
        for para in text.split("\n\n"):
            key = para.strip()[:60]
            if key and key not in seen:
                seen.add(key)
                unique_parts.append(para.strip())

    # 排序
    order = {"research": "📡", "code": "💻", "debug": "🔧", "analyze": "📊", "general": "📝"}
    sorted_results = sorted(results, key=lambda r: list(order.keys()).index(r.get("type", "general")))

    lines = [f"# 工作流结果：{original_task}", ""]
    for r in sorted_results:
        icon = order.get(r.get("type", "general"), "📝")
        cost_tag = "" if r.get("cost") == "free" else " [云端]"
        lines.append(f"## {icon} {r.get('type', 'TASK').upper()}{cost_tag}")
        text = r.get("result", "(无输出)").strip()
        lines.append(text[:2000])
        lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════

def run_workflow(task: str, context: str = "", parallel: bool = True) -> dict:
    """
    完整工作流。

    参数:
        task: 任务描述
        context: 额外上下文
        parallel: 子任务是否并行执行

    返回: { "route", "assessment", "subtasks", "results", "integrated", "token_estimate" }
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
        return {
            "route": "engineering",
            "assessment": assessment,
            "task": task,
            "message": "简单任务，直接干即可",
            "token_estimate": {"cloud": 1, "free": 0},
        }

    # 2. 拆解
    print(f"\n[拆解] 分析任务结构...")
    subtasks = _decompose(task, context)
    print(f"  拆解为 {len(subtasks)} 个子任务:")
    free_count = sum(1 for s in subtasks if s.get("cost") == "free")
    cloud_count = sum(1 for s in subtasks if s.get("cost") == "cloud")
    print(f"    其中 {free_count} 个免费（0 token），{cloud_count} 个需要云端")

    for i, st in enumerate(subtasks):
        print(f"    {i+1}. [{st['cost']}] {st['task'][:60]}...")

    # 3. 并行/串行执行
    results = []
    if parallel and len(subtasks) > 1:
        print(f"\n[执行] 并行执行 {len(subtasks)} 个子任务...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            for i, st in enumerate(subtasks):
                handler = _HANDLERS.get(st.get("handler", ""))
                if handler:
                    future = executor.submit(handler, st.get("target", st.get("task", "")))
                    futures[future] = (i, st)

            for future in as_completed(futures):
                i, st = futures[future]
                try:
                    result_text = future.result(timeout=30)
                    results.append({
                        "type": st["type"],
                        "cost": st["cost"],
                        "task": st["task"],
                        "result": result_text,
                    })
                    print(f"    ✅ 子任务 {i+1} 完成")
                except Exception as e:
                    results.append({
                        "type": st["type"],
                        "cost": st["cost"],
                        "task": st["task"],
                        "result": f"[执行失败] {e}",
                    })
                    print(f"    ❌ 子任务 {i+1} 失败: {e}")
    else:
        print(f"\n[执行] 串行执行 {len(subtasks)} 个子任务...")
        for i, st in enumerate(subtasks):
            handler = _HANDLERS.get(st.get("handler", ""))
            if handler:
                results.append({
                    "type": st["type"],
                    "cost": st["cost"],
                    "task": st["task"],
                    "result": handler(st.get("target", st.get("task", ""))),
                })
                print(f"    ✅ 子任务 {i+1} 完成")

    # 4. 整合
    print(f"\n[整合] 汇总 {len(results)} 个子任务结果...")
    integrated = _integrate(results, task)

    # 5. token估算
    token_est = {
        "cloud": cloud_count,
        "free": free_count,
        "integrated_chars": len(integrated),
    }

    print(f"  整合完成. Token估算: 云端调用 {cloud_count} 次, 免费 {free_count} 次")

    return {
        "route": "algorithm",
        "assessment": assessment,
        "subtasks": subtasks,
        "results": results,
        "integrated": integrated,
        "token_estimate": token_est,
        "task": task,
    }
