"""GitHub Agent 框架追踪器 — HTML 展示"""
import json
import os
from datetime import datetime
from config import OUTPUT_DIR, OUTPUT_HTML
from db import get_latest_stats, get_all_dates


def render_html():
    """生成带 Plotly 柱状图的 Dashboard"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    stats = get_latest_stats()
    dates = get_all_dates()

    if not stats:
        html = """<html><body><h1>📊 Agent 框架追踪器</h1>
<p>暂无数据，请先运行爬虫：<code>python agent_tracker/fetcher.py</code></p></body></html>"""
        with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"⚠️ 无数据，已生成占位页面: {OUTPUT_HTML}")
        return

    today = dates[-1] if dates else "未知"

    # 准备柱状图数据
    names = [f"{s['name']}" for s in stats]
    stars = [s["stars"] for s in stats]
    forks = [s["forks"] for s in stats]
    issues = [s["open_issues"] for s in stats]

    # 文字输出部分：Release notes + 最近活动
    text_items = []
    for s in stats:
        parts = []
        if s["latest_version"]:
            parts.append(f"🔖 **{s['name']}** v{s['latest_version']}")
            if s["latest_release_notes"]:
                notes = s["latest_release_notes"][:300]
                parts.append(f"> {notes}")
        if s["recent_activity"] and len(s["recent_activity"]) > 5:
            parts.append(f"📝 简介: {s['recent_activity'][:200]}")
        if parts:
            text_items.append("\n\n".join(parts))

    text_html = "\n\n---\n\n".join(text_items) if text_items else "暂无文字详情"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Agent 框架追踪器 - {today}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  body {{ font-family: -apple-system, 'Segoe UI', sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
  h1 {{ color: #333; }}
  .meta {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
  .chart {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .text-section {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); line-height: 1.6; }}
  .text-section h2 {{ margin-top: 0; }}
  .text-section blockquote {{ border-left: 3px solid #4a90d9; margin: 8px 0; padding: 4px 12px; color: #555; background: #f8f9fa; border-radius: 4px; }}
  .footer {{ text-align: center; color: #999; margin-top: 30px; font-size: 12px; }}
</style>
</head>
<body>

<h1>📊 开源 Agent 框架追踪器</h1>
<div class="meta">
  📅 {today} · 共 {len(stats)} 个框架 · 数据来源: GitHub API
</div>

<div class="chart" id="stars-chart"></div>
<div class="chart" id="forks-chart"></div>
<div class="chart" id="issues-chart"></div>

<div class="text-section">
  <h2>📝 文字详情（无法用柱状图展示）</h2>
  {text_html}
</div>

<div class="footer">
  自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} · Agent Tracker
</div>

<script>
// Stars 柱状图
var starsData = [{{
  x: {json.dumps(names)},
  y: {json.dumps(stars)},
  type: 'bar',
  marker: {{ color: '#4a90d9' }},
  text: {json.dumps([f'{{:,}}'.format(s) for s in stars])},
  textposition: 'auto',
}}];
var starsLayout = {{
  title: '⭐ Stars 对比',
  xaxis: {{ title: '框架' }},
  yaxis: {{ title: 'Stars' }},
  margin: {{ b: 100 }},
  paper_bgcolor: 'white',
  plot_bgcolor: 'white',
}};
Plotly.newPlot('stars-chart', starsData, starsLayout);

// Forks 柱状图
var forksData = [{{
  x: {json.dumps(names)},
  y: {json.dumps(forks)},
  type: 'bar',
  marker: {{ color: '#50b86c' }},
  text: {json.dumps([f'{{:,}}'.format(f) for f in forks])},
  textposition: 'auto',
}}];
var forksLayout = {{
  title: '🍴 Forks 对比',
  xaxis: {{ title: '框架' }},
  yaxis: {{ title: 'Forks' }},
  margin: {{ b: 100 }},
  paper_bgcolor: 'white',
  plot_bgcolor: 'white',
}};
Plotly.newPlot('forks-chart', forksData, forksLayout);

// Issues 柱状图
var issuesData = [{{
  x: {json.dumps(names)},
  y: {json.dumps(issues)},
  type: 'bar',
  marker: {{ color: '#e8634a' }},
  text: {json.dumps([str(i) for i in issues])},
  textposition: 'auto',
}}];
var issuesLayout = {{
  title: '⚠️ Open Issues 对比',
  xaxis: {{ title: '框架' }},
  yaxis: {{ title: 'Issues' }},
  margin: {{ b: 100 }},
  paper_bgcolor: 'white',
  plot_bgcolor: 'white',
}};
Plotly.newPlot('issues-chart', issuesData, issuesLayout);
</script>

</body>
</html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Dashboard 已生成: {OUTPUT_HTML}")


if __name__ == "__main__":
    render_html()
