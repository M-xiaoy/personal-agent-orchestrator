# ☁️ Personal Agent Orchestrator

> 单机多Agent调度系统 · 工程派 vs 算法派 · 文件即接口  
> 在 RTX 4060 笔记本上跑的多框架 Agent 编排实验

---

## 这是什么

一个**个人Agent调度系统**，解决的核心问题：

> 一个模型不够用，多个框架怎么协调？

当你有 Smolagents、CrewAI、Agno 这些框架都装在电脑上时，谁来决定每次任务该用哪个？

这个项目的核心思路是根据任务复杂度自动路由：简单任务走工程派直接干，复杂任务走算法派拆解后派子Agent。

---

## 核心概念

### 工程派 vs 算法派

收到任务时，先做三维度评估：

| 维度 | 低分 → 工程派 | 高分 → 算法派 |
|---|---|---|
| **确定性** | 有直接工具链可用 | 没有现成答案 |
| **推理深度** | 一问一答即可 | 需要多步推理循环 |
| **不确定性** | 答案唯一 | 多种可能性需对比 |

### 文件即接口

任务通过文件传递，不传对话历史：

```
TASK.md (任务描述 + 上下文)  ──→  子Agent  ──→  RESULT.md (执行结果)
```

- 任务文件 ≤ 1000 字，精简聚焦
- 子Agent独立执行，结果写回文件
- 调度器收结果、去重、整合、把关

---

## 项目结构

```
orchestrator/
├── core.py            # 算法派完整工作流（评估→拆解→分发→执行→整合）
├── router.py          # 路由决策器（三维度分类器）
├── dispatcher.py      # 文件即接口（任务分发/结果收集）
├── dispatch.py        # 聊天接口（创建任务入口）
├── task_queue.py      # SQLite 任务队列
├── scheduler.py       # 调度执行器（cron 每10分钟唤醒）
├── tasks/             # 任务文件目录
│   └── task_xxx/      # 单个任务
│       ├── TASK.md    #   任务描述
│       ├── RESULT.md  #   执行结果
│       └── status.json #  状态信息
├── tasks.db           # 任务数据库
└── README.md          # 项目说明
```

---

## 快速开始

### 一键运行工作流

```python
from core import run_workflow

# 算法派：拆解→并行执行→整合
result = run_workflow("对比AutoGPT和CrewAI的设计理念")
print(result["route"])        # → "algorithm"
print(result["integrated"])   # → 整合后的结果

# 工程派：直接返回
result = run_workflow("查一下AutoGPT的stars")
print(result["route"])        # → "engineering"
```

### 路由决策器

```bash
python -c "from router import assess_complexity; print(assess_complexity('对比AutoGPT和CrewAI'))"
```

### 手动调度

```bash
cd orchestrator && python scheduler.py
```

---

## 工作流程

```
收到任务
  ↓
三维度复杂度评估
  ↓
工程派 ──────────→ 直接执行 ──→ 交付
  ↓
算法派
  ↓
拆解为子任务 ──→ 写TASK.md ──→ 分配子Agent
  ↓                                ↓
整合结果 ←── 读RESULT.md ←── 子Agent执行
  ↓
我把关 ──→ 交付
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

## 许可证

MIT
