"""GitHub Agent 框架追踪器 — 配置"""
import os

# 要追踪的 Agent 框架列表 (owner/repo)
REPOS = [
    ("Significant-Gravitas", "AutoGPT"),
    ("crewAIInc", "crewAI"),
    ("All-Hands-AI", "OpenHands"),
    ("langchain-ai", "langgraph"),
    ("agno-agi", "agno"),
    ("huggingface", "smolagents"),
]

# 数据库路径
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "agent_stats.db")

# 输出 HTML 路径
OUTPUT_DIR = os.path.join(DB_DIR, "output")
OUTPUT_HTML = os.path.join(OUTPUT_DIR, "dashboard.html")

# GitHub API（无需 token 也能请求，但限流 60次/小时，够用）
GITHUB_API = "https://api.github.com/repos"
