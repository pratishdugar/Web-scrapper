"""Serialise scrape results to JSON, CSV, Markdown or plain text."""

import csv
import io
import json

FORMATS = ("json", "csv", "md", "txt")


def to_json(results):
    return json.dumps(results, indent=2, ensure_ascii=False)


def flatten(results):
    """Yield (page, type, value, detail) rows for CSV."""
    for r in results:
        page = r["url"]
        if r.get("status") != "ok":
            yield page, "error", r.get("error", ""), ""
            continue
        for key in ("title", "description", "text"):
            if r.get(key):
                yield page, key, r[key], ""
        for h in r.get("headings", []):
            yield page, f"h{h['level']}", h["text"], ""
        for l in r.get("links", []):
            yield page, "link", l["url"], l["text"]
        for i in r.get("images", []):
            yield page, "image", i["url"], i["alt"]
        for n, table in enumerate(r.get("tables", []), 1):
            for row in table:
                yield page, f"table{n}", " | ".join(row), ""
        for s in r.get("selected", []):
            yield page, "selected", s, ""


def to_csv(results):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["page", "type", "value", "detail"])
    writer.writerows(flatten(results))
    return out.getvalue()


def to_markdown(results):
    lines = []
    for r in results:
        lines.append(f"# {r.get('title') or r['url']}")
        lines.append(f"<{r['url']}>\n")
        if r.get("status") != "ok":
            lines.append(f"**Error:** {r.get('error')}\n")
            continue
        if r.get("description"):
            lines.append(f"> {r['description']}\n")
        if r.get("headings"):
            lines.append("## Headings")
            lines += [f"{'  ' * (h['level'] - 1)}- {h['text']}" for h in r["headings"]]
            lines.append("")
        if r.get("text"):
            lines += ["## Text", r["text"], ""]
        if r.get("links"):
            lines.append("## Links")
            lines += [f"- [{l['text'] or l['url']}]({l['url']})" for l in r["links"]]
            lines.append("")
        if r.get("images"):
            lines.append("## Images")
            lines += [f"- ![{i['alt']}]({i['url']})" for i in r["images"]]
            lines.append("")
        for n, table in enumerate(r.get("tables", []), 1):
            lines.append(f"## Table {n}")
            for idx, row in enumerate(table):
                lines.append("| " + " | ".join(row) + " |")
                if idx == 0:
                    lines.append("|" + " --- |" * len(row))
            lines.append("")
        if r.get("selected"):
            lines.append("## Selected")
            lines += [f"- {s}" for s in r["selected"]]
            lines.append("")
    return "\n".join(lines)


def to_text(results):
    out = io.StringIO()
    for page, kind, value, detail in flatten(results):
        out.write(f"[{kind}] {value}" + (f"  ({detail})" if detail else "") + "\n")
    return out.getvalue()


def export(results, fmt):
    try:
        return {"json": to_json, "csv": to_csv, "md": to_markdown, "txt": to_text}[fmt](results)
    except KeyError:
        raise ValueError(f"Unknown format '{fmt}'. Choose from: {', '.join(FORMATS)}")
