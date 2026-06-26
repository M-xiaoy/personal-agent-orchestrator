"""
orchestrator/router.py — 工程派 vs 算法派 路由决策器
======================================================
接收一个任务描述，输出路由决策：走工程派还是算法派。
"""

import json
import re
from pathlib import Path


# ── 路由决策 ──────────────────────────────────────────────

def assess_complexity(task: str) -> dict:
    """
    三维度复杂度评估，返回路由决策。

    返回:
        {
            "route": "engineering" | "algorithm",
            "dimensions": {
                "determinism": 0-1,     # 确定性（1=完全确定）
                "reasoning_depth": 0-1, # 推理深度（1=需要多步推理）
                "uncertainty": 0-1,     # 不确定性（1=多个可能性）
            },
            "reason": "..."
        }
    """
    task_lower = task.lower()

    # ── 关键词信号 ──────────────────────────────────────
    # 高确定性的信号（直接执行即可）
    high_determinism_signals = [
        r"查[一0-9]*(下|看|找|询)", r"搜索", r"搜一下",
        r"打开", r"读取", r"列出", r"显示",
        r"爬虫", r"爬取", r"下载",
        r"生成[一0-9]*图", r"画[一0-9]*",
        r"翻译", r"格式化", r"转换",
    ]

    # 高推理深度的信号（需要多步思考）
    high_reasoning_signals = [
        r"对比", r"比较", r"分析", r"评估",
        r"设计", r"架构", r"方案",
        r"为什么", r"原因", r"根因",
        r"排查", r"诊断", r"调试", r"排障",
        r"规划", r"计划", r"路线图",
    ]

    # 高不确定性的信号（多个可能答案）
    high_uncertainty_signals = [
        r"推荐", r"建议", r"哪个[更最好佳]",
        r"优缺点", r"优劣", r"权衡", r"trade.?off",
        r"发展方向", r"趋势", r"前景",
        r"你觉得", r"你的看法", r"怎么选",
    ]

    # ── 计算得分 ────────────────────────────────────────
    determinism = _score_signals(task_lower, high_determinism_signals, positive=True)
    reasoning = _score_signals(task_lower, high_reasoning_signals, positive=True)
    uncertainty = _score_signals(task_lower, high_uncertainty_signals, positive=True)

    # 减分项：如果任务很短 + 没有复杂信号 → 降复杂度
    if len(task) < 30 and not any([
        re.search(p, task_lower) for p in high_reasoning_signals + high_uncertainty_signals
    ]):
        reasoning *= 0.5
        uncertainty *= 0.5

    # ── 综合判断 ────────────────────────────────────────
    complexity_score = (reasoning + uncertainty) * (1 - determinism * 0.3)
    use_algorithm = complexity_score > 0.4

    return {
        "route": "algorithm" if use_algorithm else "engineering",
        "dimensions": {
            "determinism": round(determinism, 2),
            "reasoning_depth": round(reasoning, 2),
            "uncertainty": round(uncertainty, 2),
        },
        "reason": _generate_reason(use_algorithm, determinism, reasoning, uncertainty),
    }


def _score_signals(text: str, patterns: list, positive: bool = True) -> float:
    """计算文本匹配模式的程度"""
    score = 0.0
    for p in patterns:
        if re.search(p, text):
            score += 0.25
    return min(score, 1.0)


def _generate_reason(use_algo: bool, det: float, rea: float, unc: float) -> str:
    if use_algo:
        reasons = []
        if rea > 0.3:
            reasons.append(f"需要多步推理（{rea:.0%}）")
        if unc > 0.3:
            reasons.append(f"存在不确定性（{unc:.0%}）")
        if det < 0.3:
            reasons.append(f"无直接工具链可用")
        return " → 算法派：" + "、".join(reasons)
    else:
        if det > 0.5:
            return f"有直接工具链可用（确定性{det:.0%}） → 工程派"
        else:
            return f"任务简单直接 → 工程派"
