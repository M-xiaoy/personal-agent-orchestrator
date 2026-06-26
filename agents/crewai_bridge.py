"""
CrewAI bridge — 多角色协作，适合 analyze / collaborate 类任务。
本地用 deepseek-r1:7b，云端回退 DeepSeek API。
"""
import sys, warnings
sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore", category=UserWarning, module="crewai")

from agents.base import AgentBridge
from agents.defaults import resolve_model, OLLAMA_BASE


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
        return task_type in ("analyze", "research", "collaborate")

    def run(self, task: str, context: str = "", model: str = "auto") -> str:
        if not self.is_available():
            return "[CrewAI] 未安装，无法执行"

        if model == "cloud":
            cfg = resolve_model(model)
            if not cfg["api_key"]:
                return "[CrewAI] 云模式要求设置 DEEPSEEK_API_KEY 环境变量"
            from openai import OpenAI
            client = OpenAI(
                api_key=cfg["api_key"],
                base_url=cfg["base_url"],
            )
            # CrewAI LLM with openai-compatible provider
            llm = self._llm_cls(
                model=cfg["model"],
                base_url=cfg["base_url"],
                api_key=cfg["api_key"],
                temperature=0.3,
            )
        else:
            llm = self._llm_cls(
                model="ollama/deepseek-r1:7b",
                base_url=OLLAMA_BASE,
                api_key="ollama",
                temperature=0.3,
            )

        agent_role, agent_goal, agent_backstory = self._infer_role(task)

        analyst = self._agent_cls(
            role=agent_role,
            goal=agent_goal,
            backstory=agent_backstory,
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

        full_description = f"{context}\n\n{task}" if context else task
        if len(full_description) > 3000:
            full_description = full_description[:3000] + "\n\n[上下文被截断]"

        crew_task = self._task_cls(
            description=full_description,
            expected_output="一个完整、有条理的分析结果，包含关键发现和结论。",
            agent=analyst,
        )

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
        t = task.lower()
        if any(w in t for w in ["对比", "比较", "vs", "versus", "优缺点"]):
            return ("分析研究员", "全面对比两个或多个对象的异同",
                    "你擅长系统性对比分析，能从多个维度拆解问题。")
        elif any(w in t for w in ["设计", "架构", "方案", "规划"]):
            return ("架构设计师", "设计合理的方案或架构",
                    "你有丰富的系统设计经验，善于权衡取舍。")
        elif any(w in t for w in ["推荐", "建议", "哪个好"]):
            return ("技术顾问", "根据用户需求给出最佳推荐",
                    "你了解各种技术的优缺点，能结合用户场景给出建议。")
        else:
            return ("研究员", "对给定任务进行深入分析",
                    "你是一个严谨的研究员，善于从多角度分析问题。")
