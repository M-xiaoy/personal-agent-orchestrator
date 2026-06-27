# ☁️ Personal Agent Orchestrator

> 单机多Agent编排系统 · 传感器驱动路由 · 实时并行+离线调度
> 在 RTX 4060 笔记本上跑的多框架 Agent 编排实验

---

## 这是什么

一个**单机 Agent 编排系统**，解决的核心问题：

> 一个模型不够用，装了五六个框架，谁来管路由？

当 Smolagents、CrewAI、Agno 都装在电脑上，决策逻辑怎么选框架、怎么调度资源、怎么不做重复工作？这个项目给出了答案。

### 同一套内核，两种使用路径

```
┌─────────────────────────────────────────────────────┐
│                   路由决策引擎                        │
│        (三维度分类: 确定性/推理深度/不确定性)         │
└─────────────────────────────────────────────────────┘
         ↙                            ↘
┌─────────────────┐          ┌─────────────────┐
│  ① 实时协作调用   │          │  ② 离线调度执行   │
│                  │          │                  │
│  对话中直接调用   │          │  cron 定时唤醒    │
│  我拆任务→派Agent │          │  队列任务自动执   │
│  等结果→整合你看  │          │  支持前台/后台分离 │
└─────────────────┘          └─────────────────┘
         ↕                            ↕
┌─────────────────────────────────────────────────────┐
│               Agent 桥接层 (抽象接口)                 │
│   Smolagents │ CrewAI │ Agno │ LangGraph │ Vision   │
└─────────────────────────────────────────────────────┘
         ↕
┌─────────────────────────────────────────────────────┐
│              溪流传感器层 (可选数据源)                 │
│     环境感知 → 信号提取 → 上下文喂给路由决策          │
└─────────────────────────────────────────────────────┘
```

**① 实时协作** — 我在对话中直接用 `run_agent()` 派任务给子Agent并行跑，结果回来我整合。适合分析、研究、代码生成等需要多Agent配合的场景。

**② 离线调度** — 调度器通过任务队列自动执行机械任务（爬数据、定时查询、批量处理），我在对话中不受干扰。

两种模式共享同一套 Agent 桥接层和路由引擎——不是两套系统，是两套入口。

---

## 核心概念

### 工程派 vs 算法派

收到任务时，路由器先做三维度评估：

| 维度 | 低分 → 工程派 | 高分 → 算法派 |
|---|---|---|
| **确定性** | 有直接工具链可用 | 没有现成答案 |
| **推理深度** | 一问一答即可 | 需要多步推理循环 |
| **不确定性** | 答案唯一 | 多种可能性需对比 |

- **工程派**：走调度器直执行，或直接调用Agent → 快速交付
- **算法派**：拆解为子任务 → Agent并行执行 → 整合结果 → 交付

### Agent 桥接层

每个框架只需实现4个方法就能被注册使用：

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
| `vision` | VisionBridge | 图片分析 + 视觉理解 |
| `plan` | LangGraph | 状态机 + 条件分支编排 |
| `general` | Smolagents | 轻量通用 |

### Token 成本分级

```
free ──── 爬虫/拉数据/跑代码   (子进程/API，0 token)
  ↓
cloud ─── 分析/对比/决策      (Agent 框架 + 本地 Ollama)
  ↓
free ──── 去重/整合           (本地 Python 规则，0 token)
```

机械活儿交给子进程和本地模型，推理活儿交给云端和我。一分钱花对地方。

### 文件即接口（离线模式）

任务通过文件传递，不传对话历史：

```
TASK.md (任务描述 + 上下文)  ──→  子Agent  ──→  RESULT.md (执行结果)
```

适合后台批处理、定时任务、需要独立运行的复杂作业。

---

## 项目结构

```
orchestrator/
├── core.py            # 算法派完整工作流（路由→拆解→分发→Agent执行→整合）
├── router.py          # 路由决策器（三维度分类器）
├── dispatcher.py      # 文件即接口（任务文件管理 + Agent直接调用）
├── dispatch.py        # 聊天接口（创建任务、查状态、直接运行Agent）
├── task_queue.py      # SQLite 任务队列
├── scheduler.py       # 调度执行器（cron唤醒，可选后台运行）
│
├── agents/            # Agent桥接层
│   ├── __init__.py    #   统一导出
│   ├── base.py        #   抽象接口 (AgentBridge)
│   ├── registry.py    #   发现/路由/选择可用框架
│   ├── smolagents_bridge.py  # Smolagents 封装
│   ├── crewai_bridge.py      # CrewAI 封装
│   ├── agno_bridge.py        # Agno 封装
│   └── langgraph_bridge.py   # LangGraph 封装
│   └── vision_bridge.py      # 视觉模型封装 (Qwen3-VL / DeepSeek V4 Pro)
│
├── tasks/             # 任务文件目录
├── tasks.db           # 任务数据库
└── README.md          # 项目说明
```

---

## 快速开始

### 实时调用（对话中使用）

```python
from dispatch import run_agent

# 自动选框架
result = run_agent("对比 Smolagents 和 CrewAI", task_type="analyze")
print(result)

# 指定框架
result = run_agent("写一个快速排序", task_type="code", prefer="smolagents")

# 视觉任务
result = run_agent("描述这张图", task_type="vision")

# 复杂编排
result = run_agent("分析本周趋势并生成报告", task_type="plan", prefer="langgraph")
```

### 调度器离线处理

```python
from dispatch import dispatch

# 创建任务，调度器会捡起来执行
tid = dispatch("agent_task", {
    "task": "每小时抓一次 GitHub Trending",
    "task_type": "crawl",
})
```

### 通过文件接口

```python
from dispatcher import dispatch_and_execute

info = dispatch_and_execute("统计日志中的错误频率", sub_agent="crewai")
print(info["result"])
```

### 路由决策测试

```bash
python -c "from router import assess_complexity; print(assess_complexity('对比框架'))"
```

---

## 溪流联动（可选）

本系统可选择接入溪流传感器数据作为上下文输入：

```
溪流传感器 → 环境信号 （窗口/进程/时段/电池）
        ↓
信号提取层 → 精炼为场景上下文
        ↓
路由决策引擎 → 带上下文评估任务复杂度
        ↓
Agent桥接层 → 执行
```

- 传感器采集环境数据（窗口焦点、活跃进程、时段、电量）
- 信号层提取关键事件（长时段离线、电池低、活跃窗口变化）
- 可作为任务上下文的输入，辅助路由决策

---

## 当前 Agent 框架支持

| 框架 | 版本 | 桥接层 | 本地模型 |
|---|---|---|---|
| ✅ Smolagents | 1.26.0 | agents/smolagents_bridge.py | Ollama qwen2.5:7b |
| ✅ CrewAI | 1.15.0 | agents/crewai_bridge.py | Ollama qwen2.5:7b |
| ✅ Agno | 2.6.19 | agents/agno_bridge.py | Ollama qwen2.5:7b |
| ✅ LangGraph | 1.2.6 | agents/langgraph_bridge.py | Ollama qwen2.5:7b |
| ✅ Vision | — | agents/vision_bridge.py | Ollama qwen3-vl:4b / DeepSeek V4 Pro |
| ⏳ OpenHands | 需Docker | — | — |

---

## 作品集视角

这个项目展示了：

- **分层架构设计** — 桥接层抽象、路由决策器、执行后端三层解耦
- **传感器驱动调度** — 非纯规则调度，融入环境上下文
- **多框架统一抽象** — 4种不同Agent框架通过统一接口接入
- **实时+异步双模式** — 同一套内核支持两种使用场景
- **Token成本意识** — 机械任务与推理任务分开计价，不浪费token

---

## 许可证

MIT
