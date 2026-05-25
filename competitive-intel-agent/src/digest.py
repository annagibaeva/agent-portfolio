from __future__ import annotations
from collections import Counter
from html import escape


def email_subject(commentary: dict, week: str) -> str:
    counts = Counter(c["tag"] for c in commentary.get("changes", [])
                     if c.get("tag") and c["tag"] != "Noise")
    wk = week.split("-")[-1]
    if not counts:
        return f"Competitive Intel {wk} — quiet week"
    parts = [f"{n} {tag}" for tag, n in counts.most_common()]
    return f"Competitive Intel {wk} — " + ", ".join(parts)


def render_digest(results, commentary: dict, week: str,
                  failed: list[tuple[str, str]], stale: list[str]) -> str:
    syn = commentary.get("synthesis", {})
    by_index = {c["index"]: c for c in commentary.get("changes", [])}
    lines = [f"# Competitive Intel — {week}", ""]
    ok = sum(1 for r in results if r.ok)
    lines.append(f"Sources: {ok} ok / {len(failed)} failed")
    lines.append("")

    lines.append("## Weekly synthesis")
    for theme in syn.get("themes", []):
        lines.append(f"- **Theme:** {theme}")
    if syn.get("suggested_response"):
        lines.append(f"- **Suggested response:** {syn['suggested_response']}")
    lines.append("")

    if syn.get("prior_watchlist_status"):
        lines.append("## Last week's watchlist")
        for item in syn["prior_watchlist_status"]:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Changes by competitor")
    idx = 0
    for r in results:
        if not r.ok:
            continue
        if r.seeded:
            lines.append(f"### {r.name}\n- _Seeded — tracking starts next week._")
            continue
        if not r.changes:
            lines.append(f"### {r.name}\n- _No changes this week._")
            continue
        lines.append(f"### {r.name}")
        noise = 0
        for ch in r.changes:
            c = by_index.get(idx, {})
            idx += 1
            tag = c.get("tag", "Table stakes")
            if tag == "Noise":
                noise += 1
                continue
            flag = "  ⚠️ needs review" if c.get("confidence", 1.0) < 0.8 else ""
            kind = ch.kind.capitalize()
            lines.append(
                f"- [{tag}] ({kind}) {c.get('so_what','')}  "
                f"({ch.entry.title}, {ch.entry.entry_date}, {ch.entry.url}){flag}")
        if noise:
            lines.append(f"\nNoise this week: {noise} changes (not shown)")
    lines.append("")

    if failed:
        lines.append("## ⚠️ Sources unavailable this week")
        for name, err in failed:
            lines.append(f"- {name} — {err}")
        lines.append("")
    if stale:
        lines.append("## 🔧 Sources needing attention")
        for name in stale:
            lines.append(
                f"- {name} — no entries for 3 consecutive runs; check css_hint / URL")
        lines.append("")
    return "\n".join(lines)


def render_html(markdown_text: str) -> str:
    return f"<html><body><pre>{escape(markdown_text)}</pre></body></html>"
