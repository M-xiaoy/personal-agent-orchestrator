"""
Agno bridge — 多模态 + 工具链，适合 research / general 任务。
本地用 qwen2.5:7b，云端回退 DeepSeek API。
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from agents.base import AgentBridge
from agents.defaults import resolve_model


class AgnoBridge(AgentBridge):

    @property
    def name(self) -> str:
        return "agno"

    def is_available(self) -> bool:
        try:
            from agno.agent import Agent
            from agno.models.openai import OpenAIChat
            self._agent_cls = Agent
            self._model_cls = OpenAIChat
            return True
        except ImportError:
            return False

    def supports(self, task_type: str) -> bool:
        return task_type in ("research", "general", "analyze")

    def run(self, task: str, context: str = "", model: str = "auto") -> str:
        if not self.is_available():
            return "[Agno] 未安装，无法执行"

        cfg = resolve_model(model)
        if model == "cloud" and not cfg["api_key"]:
            return "[Agno] 云模式要求设置 DEEPSEEK_API_KEY 环境变量"

        llm = self._model_cls(
            id=cfg["model"],
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
        )

        full_task = f"{context}\n\n{task}" if context else task
        if len(full_task) > 3000:
            full_task = full_task[:3000] + "\n\n[上下文被截断]"

        agent = self._agent_cls(
            model=llm,
            add_name_to_context=False,
            add_history_to_context=False,
            description="你是一个全能助手，能处理各类任务。",
            markdown=True,
        )

        try:
            result = agent.run(full_task)
            return result.content if hasattr(result, "content") else str(result)
        except Exception as e:
            return f"[Agno] 执行失败: {e}"
