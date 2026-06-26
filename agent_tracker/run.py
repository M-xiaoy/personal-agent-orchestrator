"""GitHub Agent 框架追踪器 — 一键运行"""
import io
import sys

# 解决 Windows GBK 终端 emoji 输出问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from db import init_db
from fetcher import run as fetch
from render import render_html


def main():
    print("=" * 45)
    print("Agent Agent 框架追踪器")
    print("=" * 45)

    # 1. 初始化数据库
    print("\n[DB] 初始化数据库...")
    init_db()
    print("[OK] 就绪")

    # 2. 爬取数据
    fetch()

    # 3. 生成报告
    print("\n[HTML] 生成 Dashboard...")
    render_html()

    print("\n[DONE] 完成！打开以下文件查看：")
    print("   agent_tracker/output/dashboard.html")


if __name__ == "__main__":
    main()
