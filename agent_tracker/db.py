"""GitHub Agent 框架追踪器 — SQLite 存储"""
import sqlite3
from datetime import datetime
from config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            repo_owner TEXT NOT NULL,
            repo_name TEXT NOT NULL,
            stars INTEGER NOT NULL,
            forks INTEGER NOT NULL,
            open_issues INTEGER NOT NULL,
            latest_version TEXT DEFAULT '',
            latest_release_notes TEXT DEFAULT '',
            recent_activity TEXT DEFAULT '',
            UNIQUE(date, repo_owner, repo_name)
        )
    """)
    conn.commit()
    conn.close()


def save_snapshot(owner: str, name: str, stats: dict):
    """保存一次快照"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO daily_snapshots
        (date, repo_owner, repo_name, stars, forks, open_issues,
         latest_version, latest_release_notes, recent_activity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d"),
        owner,
        name,
        stats.get("stars", 0),
        stats.get("forks", 0),
        stats.get("open_issues", 0),
        stats.get("latest_version", ""),
        stats.get("latest_release_notes", ""),
        stats.get("recent_activity", ""),
    ))
    conn.commit()
    conn.close()


def get_history(days: int = 14) -> list[dict]:
    """获取最近 N 天的历史数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    sql = '''
        SELECT date, repo_owner, repo_name, stars, forks, open_issues
        FROM daily_snapshots
        WHERE date >= date('now', ?)
        ORDER BY date, repo_name
    '''
    cursor.execute(sql, (f'-{days} days',))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "date": r[0],
            "owner": r[1],
            "name": r[2],
            "stars": r[3],
            "forks": r[4],
            "open_issues": r[5],
        }
        for r in rows
    ]


def get_latest_stats() -> list[dict]:
    """获取今日最新数据（含文字详情）"""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT repo_owner, repo_name, stars, forks, open_issues,
               latest_version, latest_release_notes, recent_activity
        FROM daily_snapshots
        WHERE date = ?
        ORDER BY stars DESC
    """, (today,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "owner": r[0],
            "name": r[1],
            "stars": r[2],
            "forks": r[3],
            "open_issues": r[4],
            "latest_version": r[5],
            "latest_release_notes": r[6],
            "recent_activity": r[7],
        }
        for r in rows
    ]


def get_all_dates() -> list[str]:
    """获取所有有数据的日期"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM daily_snapshots ORDER BY date")
    dates = [r[0] for r in cursor.fetchall()]
    conn.close()
    return dates
