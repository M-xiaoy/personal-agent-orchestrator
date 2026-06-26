"""
Agent bridge: abstract interface that all framework wrappers implement.
"""
from abc import ABC, abstractmethod
from typing import Optional


class AgentBridge(ABC):
    """统一Agent接口——任何框架只需实现这4个方法就能被调度器调用。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """框架名称，例如 "smolagents"、"crewai"、"agno" """
        ...

    @abstractmethod
    def run(self, task: str, context: str = "", model: str = "auto") -> str:
        """
        执行一个任务，返回结果文本。
        
        参数:
            task: 任务描述
            context: 额外上下文
            model: "auto" | "local" | "cloud" — 模型偏好
        """
        ...

    @abstractmethod
    def supports(self, task_type: str) -> bool:
        """
        返回此框架是否擅长处理某类任务。
        task_type: "code" | "analyze" | "research" | "collaborate" | "general"
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """此框架能否在当前环境运行（依赖检查 + 模型可用性）。"""
        ...
