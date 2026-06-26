"""
LangGraph bridge — 状态机流程，适合 plan / complex / sequential 任务。
核心价值：条件分支 + 循环 + 断点续传（其他框架不具备的能力）。
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from typing import TypedDict, Literal, Annotated
from agents.base import AgentBridge


class LangGraphBridge(AgentBridge):

    @property
    def name(self) -> str:
        return "langgraph"

    def is_available(self) -> bool:
        try:
            from langgraph.graph import StateGraph, START, END
            from langgraph.checkpoint.memory import MemorySaver
            from langchain_ollama import ChatOllama
            self._graph_cls = StateGraph
            self._start = START
            self._end = END
            self._saver_cls = MemorySaver
            self._llm_cls = ChatOllama
            return True
        except ImportError:
            return False

    def supports(self, task_type: str) -> bool:
        return task_type in ("plan", "complex", "sequential")

    def run(self, task: str, context: str = "", model: str = "auto") -> str:
        if not self.is_available():
            return "[LangGraph] 未安装，无法执行"

        llm = self._llm_cls(
            model="qwen2.5:7b" if model in ("auto", "local") else "gpt-4o",
            base_url="http://localhost:11434",
            temperature=0.3,
            num_predict=1024,
        )

        from langgraph.graph import StateGraph, START, END
        from langgraph.checkpoint.memory import MemorySaver
        from langchain_core.messages import HumanMessage, SystemMessage

        # ── 状态定义 ──
        class TaskState(TypedDict):
            task: str
            plan: str
            result: str
            done: bool

        # ── 节点 ──
        def make_plan(state: TaskState) -> dict:
            """分析任务，输出执行计划"""
            msg = SystemMessage(
                content="分析以下任务，用一条简短中文说明你要怎么做。直接说方案，不客套。"
            )
            resp = llm.invoke([msg, HumanMessage(content=state["task"])])
            return {"plan": resp.content.strip()[:500]}

        def execute(state: TaskState) -> dict:
            """按计划执行"""
            msg = SystemMessage(content="执行计划并给出结果。简洁，直接回答。")
            plan_text = state.get("plan", "")
            prompt = f"任务：{state['task']}\n计划：{plan_text}\n请直接执行并输出结果。"
            resp = llm.invoke([msg, HumanMessage(content=prompt)])
            return {"result": resp.content.strip()[:3000], "done": True}

        def should_end(state: TaskState) -> Literal["execute", "__end__"]:
            if state.get("done"):
                return "__end__"
            return "execute"

        # ── 构建图 ──
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

        # ── 执行 ──
        full_task = f"{context}\n\n{task}" if context else task
        try:
            result = graph.invoke(
                {"task": full_task, "plan": "", "result": "", "done": False},
                {"configurable": {"thread_id": "default"}, "recursion_limit": 10},
            )
            return result.get("result", "（无输出）")
        except Exception as e:
            return f"[LangGraph] 执行失败: {e}"
