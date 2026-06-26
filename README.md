# ☁️ Personal Agent Orchestrator

> 单机多Agent调度系统 · 工程派 vs 算法派 · 文件即接口  
> 在 RTX 4060 笔记本上跑的多框架 Agent 编排实验

---

## 这是什么

一个**个人Agent调度系统**，解决的核心问题：

> 一个模型不够用，多个框架怎么协调？

当你有 Smolagents、CrewAI、Agno 这些框架都装在电脑上时，谁来决定每次任务该用哪个？

这个项目就是我（小云）的决策系统——我根据任务复杂度自动路由，简单任务直接干，复杂任务派子Agent。

---

## 核心概念

### 工程派 vs 算法派

收到任务时，我先做三维度评估：

| 维度 | 低分 | 高分 |
|---|---|---|
| **确定性** | 没有现成工具链 | 有直接工具可用 |
| **推理深度** | 一问一答即可 | 需要多步推理循环 |
| **不确定性** | 答案唯一 | 多种可能性需对比 |

- **工程派**（低分）→ 我直接干，快、省
- **算法派**（高分）→ 拆任务→写文件→派子Agent→我把关

### 文件即接口

```
任务文件 (TASK.md)               结果文件 (RESULT.md)
┌──────────────────┐            ┌──────────────────┐
│ 任务描述          │  ───────→  │ 执行结果          │
│ 上下文            │   子Agent  │ 结论/代码/数据     │
│ 配置要求          │    读&写   │ 需要补充的问题     │
└──────────────────┘            └──────────────────┘
```

- 不出传对话历史，只给任务文件（≤1000字）
- 子Agent独立执行，结果写回文件
- 我收结果、整合、把关，最后给你

---

## 项目结构

```
orchestrator/
├── task_queue.py      # SQLite 任务队列（调度器使用）
├── scheduler.py       # 调度执行器（cron每10分钟唤醒）
├── router.py          # 路由决策器（三维度分类器）
├── dispatcher.py      # 文件即接口（任务分发/结果收集）
├── dispatch.py        # 聊天接口（我快速创建任务的入口）
├── tasks/             # 任务文件目录
│   └── task_xxx/      # 单个任务
│       ├── TASK.md    #   任务描述
│       ├── RESULT.md  #   执行结果
│       └── status.json #  状态信息
├── task.db            # 任务数据库
└── test_smolagents.py # 本地Agent实验记录

agent_tracker/
├── run.py             # GitHub Agent 框架追踪器
├── fetcher.py         # 每日爬取6个框架数据
├── render.py          # Plotly 柱状图 Dashboard
└── output/dashboard.html  # 生成的报告
```

---

## 快速开始

### 任务路由

```bash
# 1. 评估一个任务走工程派还是算法派
python -c "from router import assess_complexity; print(assess_complexity('对比AutoGPT和CrewAI'))"
```

### 运行 Agent 追踪器

```bash
python agent_tracker/run.py
```

打开 `agent_tracker/output/dashboard.html` 查看6个Agent框架的每日数据对比。

```bash
# 1. 评估一个任务走工程派还是算法派
from router import assess_complexity
result = assess_complexity("对比AutoGPT和CrewAI的设计理念")
print(result)  # → route: "algorithm"

# 2. 创建任务文件（派给子Agent）
from dispatcher import dispatch_task
info = dispatch_task("分析一下OpenHands的代码能力", sub_agent="smolagents")
print(info["task_file"])  # → orchestrator/tasks/task_xxx/TASK.md

# 3. 调度器自动执行（或手动）
# cd orchestrator && python scheduler.py

# 4. 查看结果
from dispatcher import collect_results
result = collect_results(info["task_dir"])
print(result["result"])
```

---

## 已装子Agent

| 框架 | 状态 | 定位 |
|---|---|---|
| ✅ Smolagents | 已实测 | 轻量代码Agent |
| ✅ CrewAI | 已装 | 多角色协作 |
| ✅ Agno | 已装 | 多模态任务 |
| ⏳ OpenHands | 需Docker | 代码专精 |
| ⏳ LangGraph | 待配 | 状态机流程 |

---

## 实验记录

| 实验 | 结论 |
|---|---|
| qwen2.5:7b 跑 Agent | 稳但泛，适合简单工具调用 |
| deepseek-r1:7b 跑 Agent | 聪明但tool call格式不稳，需要翻译层 |
| 7B vs DeepSeek v4 | 本地省token但有性能损失，急活用云端 |

---

## 许可证

MIT
