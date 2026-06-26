"""GitHub Agent 框架追踪器 — API 爬虫"""
import io
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from config import REPOS, GITHUB_API
from db import save_snapshot


def fetch_json(url: str) -> dict:
    """GET 请求并返回 JSON"""
    req = urllib.request.Request(url, headers={
        "User-Agent": "AgentTracker/1.0",
        "Accept": "application/vnd.github.v3+json",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def fetch_repo_data(owner: str, name: str) -> dict:
    """获取仓库基本数据"""
    data = fetch_json(f"{GITHUB_API}/{owner}/{name}")
    return {
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "recent_activity": data.get("description", "") or "",
    }


def fetch_latest_release(owner: str, name: str) -> tuple:
    """获取最新 Release 信息"""
    try:
        data = fetch_json(f"{GITHUB_API}/{owner}/{name}/releases/latest")
        version = data.get("tag_name", "")
        notes = data.get("body", "")[:500]
        return version, notes
    except (urllib.error.HTTPError, json.JSONDecodeError):
        return "", ""


def run():
    """运行一轮爬取"""
    print(f"[CRAWL] 开始爬取 {len(REPOS)} 个仓库...")
    for owner, name in REPOS:
        try:
            stats = fetch_repo_data(owner, name)
            version, notes = fetch_latest_release(owner, name)
            stats["latest_version"] = version
            stats["latest_release_notes"] = notes
            save_snapshot(owner, name, stats)
            print(f"  [OK] {owner}/{name} | stars={stats['stars']} forks={stats['forks']}")
            time.sleep(1.5)
        except Exception as e:
            print(f"  [ERR] {owner}/{name}: {e}")
    print("[DONE] 爬取完成")


if __name__ == "__main__":
    run()
