"""
CrewAI bridge — 多角色协作，适合 analyze / collaborate 类任务。
"""
import sys, warnings
from typing import Optional

sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore", category=UserWarning, module="crewai")

from agents.base import AgentBridge


class CrewAIBridge(AgentBridge):

    @property
    def name(self) -> str:
        return "crewai"

    def is_available(self) -> bool:
        try:
            from crewai import Agent, Task, Crew, LLM
            self._agent_cls = Agent
            self._task_cls = Task
            self._crew_cls = Crew
            self._llm_cls = LLM
            return True
        except ImportError:
            return False

    def supports(self, task_type: str) -> bool:
        # CrewAI 的多角色协作适合分析、对比、研究
        return task_type in ("analyze", "research", "collaborate")

    def run(self, task: str, context: str = "", model: str = "auto") -> str:
        if not self.is_available():
            return "[CrewAI] 未安装，无法执行"

        # 构建本地 LLM
        # 分析类任务用 deepseek-r1（推理更强），通用类回退 qwen2.5
        local_model = "ollama/deepseek-r1:7b"
        llm = self._llm_cls(
            model=local_model if model in ("auto", "local") else "gpt-4o",
            base_url="http://localhost:11434",
            temperature=0.3,
        )

        # 根据任务类型自动构造角色
        agent_role, agent_goal, agent_backstory = self._infer_role(task)

        # 创建 Agent
        analyst = self._agent_cls(
            role=agent_role,
            goal=agent_goal,
            backstory=agent_backstory,
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

        # 任务
        full_description = f"{context}\n\n{task}" if context else task
        if len(full_description) > 3000:
            full_description = full_description[:3000] + "\n\n[上下文被截断]"

        crew_task = self._task_cls(
            description=full_description,
            expected_output="一个完整、有条理的分析结果，包含关键发现和结论。",
            agent=analyst,
        )

        # 执行
        crew = self._crew_cls(
            agents=[analyst],
            tasks=[crew_task],
            verbose=False,
        )

        try:
            result = crew.kickoff()
            return str(result)
        except Exception as e:
            return f"[CrewAI] 执行失败: {e}"

    def _infer_role(self, task: str) -> tuple:
        """根据任务自动推断角色设定"""
        t = task.lower()

        if any(w in t for w in ["对比", "比较", "vs", "versus", "优缺点"]):
            return (
                "分析研究员",
                "全面对比两个或多个对象的异同，给出客观分析",
                "你擅长系统性对比分析，能从多个维度拆解问题，找到核心差异。"
            )
        elif any(w in t for w in ["设计", "架构", "方案", "规划"]):
            return (
                "架构设计师",
                "设计合理的方案或架构",
                "你有丰富的系统设计经验，善于权衡取舍，给出可行方案。"
            )
        elif any(w in t for w in ["推荐", "建议", "哪个好"]):
            return (
                "技术顾问",
                "根据用户需求给出最佳推荐",
                "你了解各种技术的优缺点，能结合用户场景给出中肯建议。"
            )
        else:
            return (
                "研究员",
                "对给定任务进行深入分析",
                "你是一个严谨的研究员，善于从多角度分析问题。"
            )
