"""
Smolagents bridge — 轻量代码Agent，适合 code 类任务。
"""
import sys
from typing import Optional

sys.stdout.reconfigure(encoding="utf-8")

from agents.base import AgentBridge


class SmolagentsBridge(AgentBridge):

    @property
    def name(self) -> str:
        return "smolagents"

    def is_available(self) -> bool:
        try:
            from smolagents import OpenAIServerModel, CodeAgent
            self._model_cls = OpenAIServerModel
            self._agent_cls = CodeAgent
            return True
        except ImportError:
            return False

    def supports(self, task_type: str) -> bool:
        # Smolagents CodeAgent 最擅长写代码和执行
        return task_type in ("code", "general")

    def run(self, task: str, context: str = "", model: str = "auto") -> str:
        if not self.is_available():
            return "[Smolagents] 未安装，无法执行"

        ollama_url = "http://localhost:11434/v1"
        local_model = "qwen2.5-coder:7b"  # 代码专用模型

        model_id = local_model if model in ("auto", "local") else "gpt-4o"
        api_base = ollama_url if model in ("auto", "local") else "https://api.openai.com/v1"
        api_key = "ollama" if model in ("auto", "local") else None

        llm = self._model_cls(
            model_id=model_id,
            api_base=api_base,
            api_key=api_key,
        )

        # 如果任务描述包含 "代码"、"写一个"、"实现" 等，给 CodeAgent 加 Python 工具
        task_lower = task.lower()
        use_python = any(w in task_lower for w in [
            "代码", "写一个", "实现", "编写", "脚本", "demo",
            "python", "函数", "class", "def ",
        ])

        agent = self._agent_cls(
            tools=[],
            model=llm,
            max_steps=5 if use_python else 3,
            verbosity_level=0,
            add_base_tools=use_python,  # 只有代码任务才加 Python 解释器
        )

        try:
            # 拼接上下文
            full_task = f"{context}\n\n{task}" if context else task
            if len(full_task) > 2000:
                full_task = full_task[:2000] + "\n\n[任务被截断]"

            result = agent.run(full_task)
            return str(result)
        except Exception as e:
            return f"[Smolagents] 执行失败: {e}"
