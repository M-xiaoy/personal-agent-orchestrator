"""
Vision bridge — 用 DeepSeek V4 多模态 API 识别图片。
支持 base64 或本地图片路径。
"""
import sys, os, base64
sys.stdout.reconfigure(encoding="utf-8")

from agents.base import AgentBridge
from agents.defaults import DEEPSEEK_API_KEY, DEEPSEEK_BASE


class VisionBridge(AgentBridge):

    @property
    def name(self) -> str:
        return "vision"

    def is_available(self) -> bool:
        return True  # 依赖 DeepSeek API，不需要额外安装

    def supports(self, task_type: str) -> bool:
        return task_type in ("vision",)

    def run(self, task: str, context: str = "", model: str = "auto") -> str:
        """
        识别图片。task 格式：
        "图片路径 或 base64data, 你的问题"
        """
        if not DEEPSEEK_API_KEY:
            return "[Vision] 未设置 DEEPSEEK_API_KEY 环境变量"

        # 解析 task：前部分是图片，后部分是问题
        task = f"{context}\n\n{task}" if context else task
        parts = task.split(",", 1)
        image_input = parts[0].strip()
        question = parts[1].strip() if len(parts) > 1 else "描述这张图片"

        # 判断是路径还是 base64
        if os.path.isfile(image_input):
            try:
                with open(image_input, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                # 根据扩展名判断 MIME
                ext = os.path.splitext(image_input)[1].lower()
                mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                        "gif": "gif", "webp": "webp"}.get(ext, "png")
                img_url = f"data:image/{mime};base64,{img_b64}"
            except Exception as e:
                return f"[Vision] 读取图片失败: {e}"
        else:
            # 直接作为 base64 或 URL
            img_url = image_input if image_input.startswith("http") or image_input.startswith("data:") else image_input

        # 调用 DeepSeek API
        try:
            import httpx
            resp = httpx.post(
                f"{DEEPSEEK_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-v4-pro",  # 视觉强制用 pro
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question},
                            {"type": "image_url", "image_url": {"url": img_url}},
                        ],
                    }],
                    "max_tokens": 1000,
                },
                timeout=60,
            )
            data = resp.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            return f"[Vision] API 错误: {data}"
        except Exception as e:
            return f"[Vision] 请求失败: {e}"
