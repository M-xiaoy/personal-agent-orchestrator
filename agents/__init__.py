"""
Agent bridge layer — framework-agnostic interface for Smolagents / CrewAI / Agno.
"""
from agents.base import AgentBridge
from agents.registry import get_agent, list_agents, get_agent_for_task, AVAILABLE_AGENTS

__all__ = [
    "AgentBridge",
    "get_agent",
    "list_agents",
    "get_agent_for_task",
    "AVAILABLE_AGENTS",
]
