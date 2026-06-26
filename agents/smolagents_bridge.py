"""
Smolagents bridge — 轻量代码Agent，适合 code 类任务。
本地用 qwen2.5-coder:7b，云端回退 DeepSeek API。
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from agents.base import AgentBridge
from agents.defaults import resolve_model


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
        return task_type in ("code", "general")

    def run(self, task: str, context: str = "", model: str = "auto") -> str:
        if not self.is_available():
            return "[Smolagents] 未安装，无法执行"

        cfg = resolve_model(model, "code")
        if model == "cloud" and not cfg["api_key"]:
            return "[Smolagents] 云模式要求设置 DEEPSEEK_API_KEY 环境变量"

        llm = self._model_cls(
            model_id=cfg["model"],
            api_base=cfg["base_url"],
            api_key=cfg["api_key"],
        )

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
            add_base_tools=use_python,
        )

        try:
            full_task = f"{context}\n\n{task}" if context else task
            if len(full_task) > 2000:
                full_task = full_task[:2000] + "\n\n[任务被截断]"
            result = agent.run(full_task)
            return str(result)
        except Exception as e:
            return f"[Smolagents] 执行失败: {e}"
