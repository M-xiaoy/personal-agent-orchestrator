# ☁️ Personal Agent Orchestrator

> 单机多Agent调度系统 · 工程派 vs 算法派 · 文件即接口
> 在 RTX 4060 笔记本上跑的多框架 Agent 编排实验

---

## 这是什么

一个**个人Agent调度系统**，解决的核心问题：

> 一个模型不够用，多个框架怎么协调？

当你有 Smolagents、CrewAI、Agno 都装在电脑上时，谁来决定每次任务该用哪个？

这个项目自动根据任务类型路由到最合适的框架——代码类找 Smolagents，分析类找 CrewAI，研究类找 Agno。

---

## 核心概念

### 工程派 vs 算法派

收到任务时，先做三维度评估：

| 维度 | 低分 → 工程派 | 高分 → 算法派 |
|---|---|---|
| **确定性** | 有直接工具链可用 | 没有现成答案 |
| **推理深度** | 一问一答即可 | 需要多步推理循环 |
| **不确定性** | 答案唯一 | 多种可能性需对比 |

### Agent 桥接层

每个框架只需实现4个方法就能被调度器使用：

```
AgentBridge
├── name()         → 框架名
├── run(task)      → 执行任务
├── supports(type) → 擅长哪种任务
└── is_available() → 环境是否可用
```

任务类型自动路由：

| 任务类型 | 首选框架 | 理由 |
|---|---|---|
| `code` | Smolagents | CodeAgent 代码生成+执行 |
| `analyze` | CrewAI | 多角色协作分析 |
| `research` | Agno | 工具链 + 多步骤 |
| `collaborate` | CrewAI | 多Agent协作 |
| `general` | Smolagents | 轻量通用 |

### 文件即接口

任务通过文件传递，不传对话历史：

```
TASK.md (任务描述 + 上下文)  ──→  子Agent  ──→  RESULT.md (执行结果)
```

---

## 项目结构

```
orchestrator/
├── core.py            # 算法派完整工作流（路由→拆解→分发→Agent执行→整合）
├── router.py          # 路由决策器（三维度分类器）
├── dispatcher.py      # 文件即接口（任务文件管理 + Agent直接调用）
├── dispatch.py        # 聊天接口（创建任务、查状态、直接运行Agent）
├── task_queue.py      # SQLite 任务队列
├── scheduler.py       # 调度执行器（cron每5分钟唤醒，含Agent任务类型）
│
├── agents/            # Agent桥接层
│   ├── __init__.py    #   统一导出
│   ├── base.py        #   抽象接口 (AgentBridge)
│   ├── registry.py    #   发现/路由/选择可用框架
│   ├── smolagents_bridge.py  # Smolagents 封装
│   ├── crewai_bridge.py      # CrewAI 封装
│   ├── agno_bridge.py        # Agno 封装
│   └── langgraph_bridge.py   # LangGraph 封装
│
├── tasks/             # 任务文件目录
│   └── task_xxx/
│       ├── TASK.md    #   任务描述
│       ├── RESULT.md  #   执行结果
│       └── status.json
├── tasks.db           # 任务数据库
└── README.md          # 项目说明
```

---

## 快速开始

### 直接运行 Agent

```python
from dispatch import run_agent

# 自动选框架
result = run_agent("对比 Smolagents 和 CrewAI", task_type="analyze")
print(result)

# 指定框架
result = run_agent("写一个快速排序", task_type="code", prefer="smolagents")
```

### 调度器自动处理

```python
from dispatch import dispatch

# 创建任务，调度器会捡起来执行
tid = dispatch("agent_task", {
    "task": "对比 AutoGPT 和 CrewAI 的设计理念",
    "task_type": "analyze",
})
```

### 通过文件接口

```python
from dispatcher import dispatch_and_execute

info = dispatch_and_execute("用 Python 写一个斐波那契", sub_agent="smolagents")
print(info["result"])
```

### 路由决策

```bash
python -c "from router import assess_complexity; print(assess_complexity('对比框架'))"
```

---

## 工作流程

```
收到任务
  ↓
三维度复杂度评估 (router.py)
  ↓
工程派 ──────────→ scheduler 直接执行 ──→ 交付
  │                   crawl_web / run_code / query_kb
  │                   或 agents/ 桥接层
  ↓
算法派
  ↓
拆解为子任务 (core.py)
  ├── 子任务1 (free handler)  ──→ 并行执行
  ├── 子任务2 (free handler)  ──→ 并行执行
  └── 子任务3 (agents/)       ──→ 自动选框架
  ↓
整合结果 (本地去重/排序) ──→ 交付
```

---

## Agent 框架状态

| 框架 | 版本 | 桥接层 | 本地模型 |
|---|---|---|---|
| ✅ Smolagents | 1.26.0 | agents/smolagents_bridge.py | Ollama qwen2.5:7b |
| ✅ CrewAI | 1.15.0 | agents/crewai_bridge.py | Ollama qwen2.5:7b |
| ✅ Agno | 2.6.19 | agents/agno_bridge.py | Ollama qwen2.5:7b |
| ✅ LangGraph | 1.2.6 | agents/langgraph_bridge.py | Ollama qwen2.5:7b |
| ⏳ OpenHands | 需Docker | — | — |

---

## Token 节约策略

```
free ──── 爬虫/拉数据/跑代码  (子进程/API，0 token)
  ↓
cloud ─── 分析/对比/决策      (Agent 框架 + 本地 Ollama)
  ↓
free ──── 去重/整合           (本地 Python 规则，0 token)
```

---

## 许可证

MIT
