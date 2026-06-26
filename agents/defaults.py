"""
Agent 模型配置中心 — 所有桥接层的模型偏好在此统一管理。
默认走云端（DeepSeek），本地为 fallback。
"""
import os

# ── 本地模型（Ollama） ──
LOCAL_MODELS = {
    "default": "qwen2.5:7b",
    "code": "qwen2.5-coder:7b",
    "reason": "deepseek-r1:7b",
}

OLLAMA_BASE = "http://localhost:11434"

# ── 云端模型（DeepSeek API） ──
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com/v1"

# Pro：视觉、深度推理、长上下文
# Flash：快速响应、简单任务
TIER = {
    "pro": "deepseek-v4-pro",
    "flash": "deepseek-v4-flash",
    "fallback": "deepseek-chat",
}


def cloud_config(model_name=None):
    model = model_name or TIER["pro"]
    return {
        "api_key": DEEPSEEK_API_KEY,
        "base_url": DEEPSEEK_BASE,
        "model": model,
    }


def local_config(task_type="default"):
    model = LOCAL_MODELS.get(task_type, LOCAL_MODELS["default"])
    return {
        "api_key": "***",
        "base_url": f"{OLLAMA_BASE}/v1",
        "model": model,
    }


def resolve_model(model_pref, task_type="default"):
    """
    统一解析 model 参数：
      "auto" / 不传 → 自动选 tier（复杂→pro，简单→flash）
      "pro"         → deepseek-v4-pro
      "flash"       → deepseek-v4-flash
      "local"       → 本地 Ollama
      "deepseek-chat" → deepseek-chat
      其他字符串    → 作为模型名传给 DeepSeek API
    """
    if model_pref == "pro":
        return cloud_config(TIER["pro"])
    elif model_pref == "flash":
        return cloud_config(TIER["flash"])
    elif model_pref == "local":
        return local_config(task_type)
    elif model_pref in ("deepseek-chat",):
        return cloud_config(model_pref)

    # auto 模式：按任务类型智能选
    if model_pref in ("auto", "", None):
        heavy_tasks = ("vision", "analyze", "plan", "complex")
        if task_type in heavy_tasks:
            return cloud_config(TIER["pro"])
        return cloud_config(TIER["flash"])

    # 自定义模型名
    return cloud_config(model_pref)
