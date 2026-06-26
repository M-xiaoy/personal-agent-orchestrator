"""
Agent registry — 发现可用的框架，按任务类型路由。
"""
import sys
from typing import Optional

sys.stdout.reconfigure(encoding="utf-8")

from agents.base import AgentBridge

# ── 所有桥接类的注册表（按优先级排序） ──
_AGENT_CLASSES = []


def _lazy_register():
    """延迟注册：只在首次访问时导入"""
    if _AGENT_CLASSES:
        return
    from agents.smolagents_bridge import SmolagentsBridge
    from agents.crewai_bridge import CrewAIBridge
    from agents.agno_bridge import AgnoBridge
    from agents.langgraph_bridge import LangGraphBridge
    _AGENT_CLASSES.extend([SmolagentsBridge, CrewAIBridge, AgnoBridge, LangGraphBridge])


def list_agents() -> list[dict]:
    """
    列出当前环境可用的 Agent 框架。

    返回: [{"name": "smolagents", "available": True, "supports": ["code", "general"]}, ...]
    """
    _lazy_register()
    result = []
    for cls in _AGENT_CLASSES:
        bridge = cls()
        result.append({
            "name": bridge.name,
            "available": bridge.is_available(),
            "supports": _supports_list(bridge),
        })
    return result


AVAILABLE_AGENTS = list_agents


def get_agent(name: str) -> Optional[AgentBridge]:
    """
    按名称获取 Agent 实例。
    name: "smolagents" | "crewai" | "agno"
    """
    _lazy_register()
    for cls in _AGENT_CLASSES:
        bridge = cls()
        if bridge.name == name:
            if not bridge.is_available():
                return None
            return bridge
    return None


def get_agent_for_task(task_type: str, prefer: str = "") -> Optional[AgentBridge]:
    """
    根据任务类型选择合适的 Agent。

    参数:
        task_type: "code" | "analyze" | "research" | "collaborate" | "general"
        prefer: 指定优先使用的框架（可选）

    返回: AgentBridge 实例，或 None（无可用 Agent）
    """
    _lazy_register()

    # 如果指定了优先框架且可用
    if prefer:
        bridge = get_agent(prefer)
        if bridge and bridge.supports(task_type):
            return bridge

    # 按优先级 + 支持度匹配
    for cls in _AGENT_CLASSES:
        bridge = cls()
        if bridge.is_available() and bridge.supports(task_type):
            return bridge

    return None


def _supports_list(bridge: AgentBridge) -> list[str]:
    """获取 Agent 支持的任务类型列表"""
    types = ["code", "analyze", "research", "collaborate", "general", "plan", "complex", "sequential"]
    return [t for t in types if bridge.supports(t)]
