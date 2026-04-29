def build_subject(day: int, date_str: str) -> str:
    return f"☀️ Day {day} Briefing — {date_str}"


def build_email(data: dict) -> str:
    events_html = ""
    if data.get("events_unavailable"):
        events_html = "<p>⚠️ Calendar unavailable — check manually</p>"
    elif data.get("events"):
        rows = ""
        for e in data["events"]:
            attendees = f" ({', '.join(e['attendees'])})" if len(e.get("attendees", [])) > 1 else ""
            rows += f"<tr><td style='padding:2px 12px 2px 0;color:#555'>{e['time']}</td><td>{e['title']}{attendees}</td></tr>"
        events_html = f"<table>{rows}</table>"
    else:
        events_html = "<p>No events today.</p>"

    gmail_warning = "<p>⚠️ Gmail unavailable — check manually</p>" if data.get("gmail_unavailable") else ""

    star_resources = ""
    for i, r in enumerate(data["day_content"].get("star_resources", []), 1):
        star_resources += f'<p>{i}. <a href="{r["url"]}">{r["title"]}</a></p>'

    morning_tasks = "".join(f"<li>★ {t}</li>" for t in data["day_content"].get("morning_tasks", []))
    afternoon_tasks = "".join(f"<li>{t}</li>" for t in data["day_content"].get("afternoon_tasks", []))

    anthropic_post = data.get("anthropic_post")
    post_html = ""
    if anthropic_post:
        post_html = f'• <a href="{anthropic_post["url"]}">Anthropic: {anthropic_post["title"]}</a><br>'

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
  body {{font-family: -apple-system, Arial, sans-serif; font-size: 15px; line-height: 1.5; color: #222; max-width: 600px; margin: 0 auto; padding: 20px;}}
  h2 {{font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #888; border-bottom: 1px solid #eee; padding-bottom: 4px; margin-top: 24px;}}
  a {{color: #0066cc;}}
</style></head>
<body>
<h2>PROGRESS</h2>
<p>Day {data['day']} of 21 &middot; Week {data['week']} &middot; {data['pct_complete']}% complete</p>

<h2>TODAY'S SCHEDULE</h2>
{events_html}

<h2>MEETING CONTEXT</h2>
{gmail_warning}
<p>{data.get('meeting_context', '')}</p>

<h2>TODAY'S LEARNING</h2>
<p><strong>Topic:</strong> {data['day_content']['topic']}</p>
<ul>{morning_tasks}</ul>
<p><strong>Hands-on:</strong></p>
<ul>{afternoon_tasks}</ul>
<p>Quiz: {data['day_content']['quiz_count']} questions (self-check at 16:30) &middot; Time budget: 7hrs</p>

<h2>WHAT TO READ TODAY</h2>
{star_resources}

<h2>AI PULSE</h2>
{post_html}
<p>{data.get('ai_pulse', '')}</p>
</body></html>"""
