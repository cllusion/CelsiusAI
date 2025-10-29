"""
Report formatters for Celsius AI
Provides simple, dependency-free functions to render learning
reports as human-readable text and lightweight HTML.

These are intentionally small and safe (no external templates).
"""

from typing import Dict, Any


def format_learning_report_text(report: Dict[str, Any]) -> str:
    """Return a plain-text human-readable rendering of a learning report."""
    lines = []
    period = report.get("report_period") or report.get("period") or "daily"
    lines.append(f"CELSIUS AI - LEARNING REPORT ({period.upper()})")
    lines.append("=" * 80)
    lines.append(f"Generated: {report.get('generated_at')}")
    lines.append("")

    lines.append("Executive Summary:")
    summary = report.get("learning_summary") or report.get("summary") or ""
    if summary:
        lines.append(summary)
    else:
        # Fallback synth from totals
        tc = report.get("total_content_learned") or report.get("total_content", 0)
        ti = report.get("total_insights") or report.get("insights_generated", 0)
        lines.append(f"Content learned: {tc}; Insights generated: {ti}")

    lines.append("")
    lines.append("Top Topics:")
    top = report.get("top_topics") or report.get("topics") or []
    if top:
        for t in top:
            if isinstance(t, dict):
                lines.append(f" - {t.get('topic')} ({t.get('count', t.get('Cnt', '') )})")
            else:
                lines.append(f" - {t}")
    else:
        lines.append(" - (no top topics in report)")

    lines.append("")
    lines.append("Sample Insights:")
    samples = report.get("sample_insights") or report.get("insights") or []
    if samples:
        for s in samples[:10]:
            if isinstance(s, dict):
                lines.append(
                    f" - [{s.get('topic')}] {s.get('insight')[:200]} (confidence: {s.get('confidence', 0):.2f})"
                )
            else:
                lines.append(f" - {str(s)[:200]}")
    else:
        lines.append(" - (no sample insights)")

    recs = report.get("recommendations") or []
    if recs:
        lines.append("")
        lines.append("Recommendations:")
        for r in recs:
            lines.append(f" * {r}")

    lines.append("\n" + "=" * 80)
    lines.append("End of report")
    return "\n".join(lines)


def format_learning_report_html(report: Dict[str, Any]) -> str:
    """Return a minimal HTML rendering of the learning report."""
    title = f"Celsius AI Learning Report - {report.get('report_period') or report.get('period') or 'daily'}"
    html_lines = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        f'  <meta charset="utf-8">',
        f"  <title>{title}</title>",
        "  <style>body{font-family:Segoe UI,Arial,Helvetica,sans-serif;margin:20px;color:#222} h1{color:#0b5; } .topic{margin-bottom:6px;} .insight{margin:6px 0;padding:6px;border-left:3px solid #ccc;background:#f9f9f9}</style>",
        "</head>",
        "<body>",
        f"  <h1>{title}</h1>",
        f'  <p><strong>Generated:</strong> {report.get("generated_at")}</p>',
        "  <h2>Executive Summary</h2>",
        "  <div>" + (report.get("learning_summary") or report.get("summary") or "") + "</div>",
        "  <h2>Top Topics</h2>",
        "  <ul>",
    ]

    top = report.get("top_topics") or report.get("topics") or []
    if top:
        for t in top:
            if isinstance(t, dict):
                html_lines.append(f"    <li class='topic'>{t.get('topic')} ({t.get('count', '')})</li>")
            else:
                html_lines.append(f"    <li class='topic'>{t}</li>")
    else:
        html_lines.append("    <li>(no top topics)</li>")

    html_lines.append("  </ul>")
    html_lines.append("  <h2>Sample Insights</h2>")

    samples = report.get("sample_insights") or report.get("insights") or []
    if samples:
        for s in samples[:20]:
            if isinstance(s, dict):
                html_lines.append(
                    f"  <div class='insight'><strong>[{s.get('topic')}]</strong> {s.get('insight')} <em>(confidence: {s.get('confidence', 0):.2f})</em></div>"
                )
            else:
                html_lines.append(f"  <div class='insight'>{str(s)}</div>")
    else:
        html_lines.append('  <div class="insight">(no insights)</div>')

    recs = report.get("recommendations") or []
    if recs:
        html_lines.append("  <h2>Recommendations</h2>")
        html_lines.append("  <ul>")
        for r in recs:
            html_lines.append(f"    <li>{r}</li>")
        html_lines.append("  </ul>")

    html_lines.extend(["</body>", "</html>"])
    return "\n".join(html_lines)
