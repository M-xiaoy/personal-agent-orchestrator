"""
Agent 模型配置中心 — 所有桥接层的模型偏好在此统一管理。
"""
import os

# ── 本地模型（Ollama） ──
LOCAL_MODELS = {
    "default": "qwen2.5:7b",         # 通用兜底
    "code": "qwen2.5-coder:7b",      # 代码专精
    "reason": "deepseek-r1:7b",       # 推理专精
}

OLLAMA_BASE = "http://localhost:11434"

# ── 云端模型（DeepSeek API） ──
# 通过环境变量 DEEPSEEK_API_KEY 配置，避免硬编码
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"  # 默认聊天模型

def cloud_config():
    """返回云端 DeepSeek API 的配置"""
    return {
        "api_key": DEEPSEEK_API_KEY,
        "base_url": DEEPSEEK_BASE,
        "model": DEEPSEEK_MODEL,
    }

def local_config(task_type="default"):
    """返回本地 Ollama 的配置"""
    model = LOCAL_MODELS.get(task_type, LOCAL_MODELS["default"])
    return {
        "api_key": "ollama",
        "base_url": f"{OLLAMA_BASE}/v1",
        "model": model,
    }

def resolve_model(model_pref, task_type="default"):
    """
    统一解析 model 参数：
    - "auto" / "local" → 本地模型
    - "cloud" → DeepSeek API
    - 其他 → 按需
    """
    if model_pref in ("auto", "local"):
        return local_config(task_type)
    elif model_pref == "cloud":
        return cloud_config()
    else:
        return local_config(task_type)  # fallback
