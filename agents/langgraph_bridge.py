"""
LangGraph bridge — 状态机流程，适合 plan / complex / sequential 任务。
本地用 deepseek-r1:7b，云端回退 DeepSeek API。
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from typing import TypedDict, Literal
from agents.base import AgentBridge
from agents.defaults import resolve_model, OLLAMA_BASE


class LangGraphBridge(AgentBridge):

    @property
    def name(self) -> str:
        return "langgraph"

    def is_available(self) -> bool:
        try:
            from langgraph.graph import StateGraph, START, END
            from langgraph.checkpoint.memory import MemorySaver
            from langchain_ollama import ChatOllama
            from langchain_openai import ChatOpenAI
            self._graph_cls = StateGraph
            self._start = START
            self._end = END
            self._saver_cls = MemorySaver
            self._local_llm_cls = ChatOllama
            self._cloud_llm_cls = ChatOpenAI
            return True
        except ImportError:
            return False

    def supports(self, task_type: str) -> bool:
        return task_type in ("plan", "complex", "sequential")

    def run(self, task: str, context: str = "", model: str = "auto") -> str:
        if not self.is_available():
            return "[LangGraph] 未安装，无法执行"

        if model == "cloud":
            cfg = resolve_model(model)
            if not cfg["api_key"]:
                return "[LangGraph] 云模式要求设置 DEEPSEEK_API_KEY 环境变量"
            llm = self._cloud_llm_cls(
                model=cfg["model"],
                openai_api_key=cfg["api_key"],
                openai_api_base=cfg["base_url"],
                temperature=0.3,
            )
        else:
            llm = self._local_llm_cls(
                model="deepseek-r1:7b",
                base_url=OLLAMA_BASE,
                temperature=0.3,
                num_predict=1024,
            )

        from langgraph.graph import StateGraph, START, END
        from langgraph.checkpoint.memory import MemorySaver
        from langchain_core.messages import HumanMessage, SystemMessage

        class TaskState(TypedDict):
            task: str
            plan: str
            result: str
            done: bool

        def make_plan(state: TaskState) -> dict:
            msg = SystemMessage(content="分析以下任务，用一条简短中文说明你要怎么做。直接说方案。")
            resp = llm.invoke([msg, HumanMessage(content=state["task"])])
            return {"plan": resp.content.strip()[:500]}

        def execute(state: TaskState) -> dict:
            msg = SystemMessage(content="执行计划并给出结果。简洁直接。")
            plan_text = state.get("plan", "")
            prompt = f"任务：{state['task']}\n计划：{plan_text}\n请直接执行。"
            resp = llm.invoke([msg, HumanMessage(content=prompt)])
            return {"result": resp.content.strip()[:3000], "done": True}

        def should_end(state: TaskState) -> Literal["execute", "__end__"]:
            return "__end__" if state.get("done") else "execute"

        builder = StateGraph(TaskState)
        builder.add_node("plan", make_plan)
        builder.add_node("execute", execute)
        builder.add_edge(START, "plan")
        builder.add_edge("plan", "execute")
        builder.add_conditional_edges("execute", should_end, {
            "execute": "execute",
            "__end__": END,
        })

        memory = MemorySaver()
        graph = builder.compile(checkpointer=memory)

        full_task = f"{context}\n\n{task}" if context else task
        try:
            result = graph.invoke(
                {"task": full_task, "plan": "", "result": "", "done": False},
                {"configurable": {"thread_id": "default"}, "recursion_limit": 10},
            )
            return result.get("result", "（无输出）")
        except Exception as e:
            return f"[LangGraph] 执行失败: {e}"
