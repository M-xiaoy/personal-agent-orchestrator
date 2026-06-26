"""
orchestrator/task_queue.py — 任务队列核心
=========================================
SQLite 任务队列，支持：
- 创建任务（我或调度器）
- 捡取待处理任务
- 标记完成/失败
- 查询任务状态

用法:
    from task_queue import TaskQueue
    q = TaskQueue()
    q.add("crawl_web", {"url": "..."})   # 轻量任务，调度器直接干
    q.add("need_think", {"问题": "..."}) # 等我处理
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "tasks.db"


class TaskQueue:
    def __init__(self):
        self._init_db()

    def _conn(self):
        return sqlite3.connect(str(DB_PATH))

    def _init_db(self):
        conn = self._conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                params TEXT DEFAULT '{}',
                status TEXT DEFAULT 'pending',
                result TEXT DEFAULT '',
                need_me INTEGER DEFAULT 0,
                notify INTEGER DEFAULT 1,
                created_at TEXT,
                started_at TEXT,
                done_at TEXT,
                error TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status
            ON tasks(status)
        """)
        conn.commit()
        conn.close()

    # ── 公开接口 ──────────────────────────────────────────────

    def add(self, task_type: str, params: dict = None,
            need_me: bool = False, notify: bool = True) -> str:
        """创建任务，返回任务ID"""
        task_id = str(uuid.uuid4())[:12]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        conn.execute(
            "INSERT INTO tasks (id, type, params, status, need_me, notify, created_at) "
            "VALUES (?, ?, ?, 'pending', ?, ?, ?)",
            (task_id, task_type, json.dumps(params or {}, ensure_ascii=False),
             int(need_me), int(notify), now)
        )
        conn.commit()
        conn.close()
        return task_id

    def pending(self, limit: int = 10) -> list[dict]:
        """获取待处理任务"""
        conn = self._conn()
        rows = conn.execute(
            "SELECT id, type, params, need_me, notify, created_at "
            "FROM tasks WHERE status='pending' ORDER BY created_at LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [
            {"id": r[0], "type": r[1], "params": json.loads(r[2]),
             "need_me": bool(r[3]), "notify": bool(r[4]), "created_at": r[5]}
            for r in rows
        ]

    def mark_running(self, task_id: str) -> bool:
        """标记为执行中"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        c = conn.execute(
            "UPDATE tasks SET status='running', started_at=? WHERE id=? AND status='pending'",
            (now, task_id)
        ).rowcount
        conn.commit()
        conn.close()
        return c > 0

    def mark_done(self, task_id: str, result: str = ""):
        """标记完成"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        conn.execute(
            "UPDATE tasks SET status='done', result=?, done_at=? WHERE id=?",
            (result, now, task_id)
        )
        conn.commit()
        conn.close()

    def mark_failed(self, task_id: str, error: str):
        """标记失败"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        conn.execute(
            "UPDATE tasks SET status='failed', error=?, done_at=? WHERE id=?",
            (error, now, task_id)
        )
        conn.commit()
        conn.close()

    def get(self, task_id: str) -> dict | None:
        """查询单个任务"""
        conn = self._conn()
        r = conn.execute(
            "SELECT id, type, params, status, result, need_me, notify, "
            "created_at, started_at, done_at, error FROM tasks WHERE id=?",
            (task_id,)
        ).fetchone()
        conn.close()
        if not r:
            return None
        return {
            "id": r[0], "type": r[1], "params": json.loads(r[2]),
            "status": r[3], "result": r[4], "need_me": bool(r[5]),
            "notify": bool(r[6]), "created_at": r[7],
            "started_at": r[8], "done_at": r[9], "error": r[10],
        }

    def recent(self, limit: int = 10) -> list[dict]:
        """最近任务"""
        conn = self._conn()
        rows = conn.execute(
            "SELECT id, type, status, need_me, created_at, done_at, error "
            "FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [
            {"id": r[0], "type": r[1], "status": r[2],
             "need_me": bool(r[3]), "created_at": r[4],
             "done_at": r[5], "error": r[6]}
            for r in rows
        ]

    def pending_for_me(self) -> list[dict]:
        """等我处理的任务"""
        return self.pending()  # need_me 任务标记在params里，调度器看到会跳过

    def count(self) -> dict:
        """统计各状态数量"""
        conn = self._conn()
        rows = conn.execute(
            "SELECT status, COUNT(*) FROM tasks GROUP BY status"
        ).fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}
