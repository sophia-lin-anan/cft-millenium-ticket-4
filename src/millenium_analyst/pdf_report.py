"""Printable PDF renderer built from the same report view model as HTML."""

from __future__ import annotations

from pathlib import Path


COLORS = {
    "ink": "#17211d",
    "muted": "#66716b",
    "line": "#dfe6e1",
    "paper": "#f5f7f4",
    "skilled": "#166f53",
    "skilled_bg": "#e4f3eb",
    "lucky": "#a8660b",
    "lucky_bg": "#fff2d8",
    "broken": "#9b3535",
    "broken_bg": "#f9e5e5",
    "unlucky": "#356d9c",
    "unlucky_bg": "#e7f0f8",
    "inconclusive": "#555555",
    "inconclusive_bg": "#eeeeee",
}


def render_pdf(view: dict, output_path: Path) -> None:
    try:
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.pdfgen.canvas import Canvas
    except ImportError as exc:
        raise RuntimeError("PDF rendering requires reportlab; install requirements-pdf.txt") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(output_path), pagesize=landscape(A4))
    canvas.setTitle(view["report"]["title"])
    _draw_overview(canvas, view, landscape(A4), HexColor, stringWidth)
    page_number = 2
    for pod in view["pods"]:
        canvas.setPageSize(A4)
        _draw_pod_summary(canvas, view, pod, A4, HexColor, stringWidth, page_number)
        page_number += 1
        canvas.setPageSize(A4)
        _draw_pod_support(canvas, view, pod, A4, HexColor, stringWidth, page_number)
        page_number += 1
        for action_number, action in enumerate(pod["analysis"]["recommended_actions"][1:], start=2):
            canvas.setPageSize(A4)
            _draw_action_page(
                canvas,
                view,
                pod,
                action,
                action_number,
                A4,
                HexColor,
                stringWidth,
                page_number,
            )
            page_number += 1
    canvas.save()


def _draw_overview(canvas, view, size, color, string_width) -> None:
    width, height = size
    margin = 42
    canvas.setFillColor(color(COLORS["paper"]))
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    _header(canvas, view, width, height, color)
    plot_x, plot_y, plot_w, plot_h = margin, 116, 452, 294
    half_w, half_h = plot_w / 2, plot_h / 2
    quadrants = [
        (plot_x, plot_y + half_h, "lucky", "Lucky", "Good P&L, weak measured edge"),
        (plot_x + half_w, plot_y + half_h, "skilled", "Skilled", "Good P&L, measured edge"),
        (plot_x, plot_y, "broken", "Broken", "Bad P&L, weak measured edge"),
        (plot_x + half_w, plot_y, "unlucky", "Unlucky", "Bad P&L, measured edge"),
    ]
    for x, y, key, title, copy in quadrants:
        canvas.setFillColor(color(COLORS[f"{key}_bg"]))
        canvas.rect(x, y, half_w, half_h, fill=1, stroke=0)
        canvas.setFillColor(color(COLORS["ink"]))
        canvas.setFont("Times-Bold", 17)
        canvas.drawString(x + 14, y + half_h - 25, title)
        canvas.setFillColor(color(COLORS["muted"]))
        canvas.setFont("Helvetica", 8.5)
        canvas.drawString(x + 14, y + half_h - 41, copy)
    canvas.setStrokeColor(color("#7d8781"))
    canvas.setDash(4, 4)
    canvas.line(plot_x + half_w, plot_y, plot_x + half_w, plot_y + plot_h)
    canvas.line(plot_x, plot_y + half_h, plot_x + plot_w, plot_y + half_h)
    canvas.setDash()
    max_pnl = max(10, *(abs(p["performance"]["pnl_percent"]) for p in view["pods"])) * 1.15
    for pod in view["pods"]:
        skill = pod["decision_skill"]["aggregate_percentile"]
        pnl = pod["performance"]["pnl_percent"]
        x = plot_x + (skill / 100) * plot_w
        y = plot_y + half_h + (pnl / max_pnl) * (half_h - 28)
        verdict = pod["analysis"]["verdict"]["classification"]
        canvas.setFillColor(color(COLORS.get(f"{verdict}_bg", COLORS["inconclusive_bg"])))
        canvas.setStrokeColor(color(COLORS.get(verdict, COLORS["inconclusive"])))
        canvas.setLineWidth(2)
        canvas.circle(x, y, 16, fill=1, stroke=1)
        canvas.setFillColor(color(COLORS.get(verdict, COLORS["inconclusive"])))
        canvas.setFont("Helvetica-Bold", 9)
        label = pod["pod_id"].replace("Pod ", "")
        canvas.drawCentredString(x, y - 3, label)
    canvas.setFillColor(color(COLORS["muted"]))
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(plot_x + plot_w / 2, plot_y - 20, "Decision skill vs random-portfolio baseline")
    canvas.saveState()
    canvas.translate(plot_x - 25, plot_y + plot_h / 2)
    canvas.rotate(90)
    canvas.drawCentredString(0, 0, "Performance")
    canvas.restoreState()

    list_x = plot_x + plot_w + 24
    canvas.setFillColor(color("#ffffff"))
    canvas.roundRect(list_x, plot_y, width - margin - list_x, plot_h, 14, fill=1, stroke=0)
    canvas.setFillColor(color(COLORS["ink"]))
    canvas.setFont("Times-Bold", 20)
    canvas.drawString(list_x + 18, plot_y + plot_h - 32, "Portfolio verdicts")
    row_y = plot_y + plot_h - 70
    for pod in view["pods"]:
        verdict = pod["analysis"]["verdict"]["classification"]
        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(color(COLORS["ink"]))
        canvas.drawString(list_x + 18, row_y, pod["pod_id"])
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(color(COLORS["muted"]))
        canvas.drawString(
            list_x + 18,
            row_y - 15,
            f"{pod['performance']['pnl_percent']:+.1f}% P&L | {_ordinal(pod['decision_skill']['aggregate_percentile'])} pct skill",
        )
        canvas.setFillColor(color(COLORS.get(f"{verdict}_bg", COLORS["inconclusive_bg"])))
        canvas.roundRect(list_x + 150, row_y - 7, 66, 20, 10, fill=1, stroke=0)
        canvas.setFillColor(color(COLORS.get(verdict, COLORS["inconclusive"])))
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.drawCentredString(list_x + 183, row_y, verdict.upper())
        row_y -= 61
    _footer(canvas, view, width, color, 1)
    canvas.showPage()


def _draw_pod_summary(canvas, view, pod, size, color, string_width, page_number: int) -> None:
    width, height = size
    margin = 44
    canvas.setFillColor(color("#ffffff"))
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    verdict = pod["analysis"]["verdict"]
    narrative = pod["analysis"]["narrative"]
    key = verdict["classification"]
    canvas.setFillColor(color(COLORS["ink"]))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(margin, height - 42, "AGENTIC RISK INTELLIGENCE")
    canvas.setFont("Times-Bold", 32)
    canvas.drawString(margin, height - 82, pod["pod_id"])
    canvas.setFillColor(color(COLORS.get(f"{key}_bg", COLORS["inconclusive_bg"])))
    canvas.roundRect(margin, height - 119, 82, 23, 11, fill=1, stroke=0)
    canvas.setFillColor(color(COLORS.get(key, COLORS["inconclusive"])))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawCentredString(margin + 41, height - 111, key.upper())
    canvas.setFillColor(color(COLORS["muted"]))
    canvas.setFont("Helvetica", 9)
    canvas.drawString(margin + 94, height - 112, f"{verdict['confidence'] * 100:.0f}% analyst confidence | gaming risk: {verdict['gaming_risk']}")

    canvas.setFillColor(color(COLORS["paper"]))
    canvas.roundRect(margin, height - 190, width - 2 * margin, 52, 8, fill=1, stroke=0)
    _wrapped_text(
        canvas,
        verdict["summary"],
        margin + 12,
        height - 157,
        width - 2 * margin - 24,
        9,
        color,
        string_width,
    )

    cards = [
        ("P&L", f"{pod['performance']['pnl_percent']:+.1f}%"),
        ("Decision skill", f"{_ordinal(pod['decision_skill']['aggregate_percentile'])} pct"),
        ("Max drawdown", _metric(pod, "drawdown")),
        ("Expected shortfall", _metric(pod, "expected_shortfall")),
    ]
    card_y, card_w = height - 255, (width - 2 * margin - 24) / 4
    for index, (label, value) in enumerate(cards):
        x = margin + index * (card_w + 8)
        canvas.setFillColor(color(COLORS["paper"]))
        canvas.roundRect(x, card_y, card_w, 49, 8, fill=1, stroke=0)
        canvas.setFillColor(color(COLORS["muted"]))
        canvas.setFont("Helvetica-Bold", 6.5)
        canvas.drawString(x + 10, card_y + 33, label.upper())
        canvas.setFillColor(color(COLORS["ink"]))
        canvas.setFont("Helvetica-Bold", 15)
        canvas.drawString(x + 10, card_y + 12, value)

    section_y = card_y - 34
    _section_label(canvas, margin, section_y, "CONCLUSION LOGIC", color)
    canvas.setFillColor(color(COLORS["ink"]))
    canvas.setFont("Times-Bold", 17)
    canvas.drawString(margin, section_y - 22, "How we reached this verdict")
    logic_top = section_y - 46
    column_gap = 16
    logic_w = (width - 2 * margin - column_gap) / 2
    _section_label(canvas, margin, logic_top, f"WHY {key.upper()}", color)
    left_bottom = _wrapped_text(
        canvas,
        narrative["why_this_verdict"],
        margin,
        logic_top - 17,
        logic_w,
        8.1,
        color,
        string_width,
    )
    right_x = margin + logic_w + column_gap
    _section_label(canvas, right_x, logic_top, "BEST ALTERNATIVE EXPLANATION", color)
    right_cursor = _wrapped_text(
        canvas,
        narrative["alternative_explanation"],
        right_x,
        logic_top - 17,
        logic_w,
        8.1,
        color,
        string_width,
    )
    _section_label(canvas, right_x, right_cursor - 5, "WHAT WOULD CHANGE OUR VIEW", color)
    right_bottom = _wrapped_text(
        canvas,
        narrative["what_would_change_verdict"],
        right_x,
        right_cursor - 22,
        logic_w,
        8.1,
        color,
        string_width,
    )

    signals_y = min(left_bottom, right_bottom) - 20
    canvas.setStrokeColor(color(COLORS["line"]))
    canvas.line(margin, signals_y + 9, width - margin, signals_y + 9)
    _section_label(canvas, margin, signals_y, "UNDERLYING SIGNALS", color)
    canvas.setFillColor(color(COLORS["ink"]))
    canvas.setFont("Times-Bold", 17)
    canvas.drawString(margin, signals_y - 22, "Process and risk snapshot")
    narrative_bottom = _wrapped_text(
        canvas,
        narrative["decision_skill_analysis"] + " " + narrative["risk_analysis"],
        margin,
        signals_y - 42,
        width - 2 * margin,
        8.1,
        color,
        string_width,
    )

    left_x = margin
    right_x = width / 2 + 18
    table_y = narrative_bottom - 14
    _section_label(canvas, left_x, table_y, "DECISION COMPONENTS VS CHANCE", color)
    y = table_y - 22
    for name, value in pod["decision_skill"]["components"].items():
        canvas.setFillColor(color(COLORS["muted"]))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(left_x, y, name.replace("_", " ").title())
        track_x, track_w = left_x + 90, 126
        canvas.setFillColor(color("#edf1ee"))
        canvas.roundRect(track_x, y - 1, track_w, 6, 3, fill=1, stroke=0)
        canvas.setFillColor(color(COLORS["green"] if "green" in COLORS else COLORS["skilled"]))
        if value < 50:
            canvas.setFillColor(color(COLORS["broken"]))
        canvas.roundRect(track_x, y - 1, track_w * value / 100, 6, 3, fill=1, stroke=0)
        canvas.setFillColor(color(COLORS["ink"]))
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawRightString(left_x + 248, y, _ordinal(value))
        y -= 22

    _section_label(canvas, right_x, table_y, "RISK-CORE MEASURES", color)
    risk_y = table_y - 22
    for name, metric in pod["risk_metrics"].items():
        canvas.setFillColor(color(COLORS["muted"]))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(right_x, risk_y, name.replace("_", " ").title())
        canvas.setFillColor(color(COLORS["ink"]))
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawRightString(width - margin, risk_y, _risk_value(metric))
        risk_y -= 20

    _footer(canvas, view, width, color, page_number)
    canvas.showPage()


def _draw_pod_support(canvas, view, pod, size, color, string_width, page_number: int) -> None:
    width, height = size
    margin = 44
    canvas.setFillColor(color("#ffffff"))
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    analysis = pod["analysis"]
    verdict = analysis["verdict"]["classification"]

    canvas.setFillColor(color(COLORS["ink"]))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(margin, height - 42, f"{pod['pod_id'].upper()} | {verdict.upper()}")
    canvas.setFont("Times-Bold", 28)
    canvas.drawString(margin, height - 78, "Evidence and next steps")
    canvas.setFillColor(color(COLORS["muted"]))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(margin, height - 110, "The same traceable support and advisory actions shown in the interactive report.")

    items = [(item, False) for item in analysis["evidence"]] + [
        (item, True) for item in analysis["counterevidence"]
    ]
    gap = 10
    card_w = (width - 2 * margin - gap) / 2
    card_h = 90
    start_y = height - 138
    for index, (item, counter) in enumerate(items):
        col = index % 2
        row = index // 2
        x = margin + col * (card_w + gap)
        top = start_y - row * (card_h + gap)
        canvas.setFillColor(color("#fbfaf7" if counter else "#f5f7f4"))
        canvas.roundRect(x, top - card_h, card_w, card_h, 7, fill=1, stroke=0)
        canvas.setFillColor(color(COLORS["lucky"] if counter else COLORS["skilled"]))
        canvas.setFont("Helvetica-Bold", 6.5)
        canvas.drawString(x + 10, top - 14, "COUNTEREVIDENCE" if counter else "SUPPORTING EVIDENCE")
        canvas.setFillColor(color(COLORS["muted"]))
        canvas.setFont("Courier", 5.8)
        canvas.drawString(x + 10, top - 26, item["metric_id"])
        cursor = _wrapped_text(
            canvas,
            item["observation"],
            x + 10,
            top - 40,
            card_w - 20,
            7.2,
            color,
            string_width,
        )
        _wrapped_text(
            canvas,
            "Why it matters: " + item["interpretation"],
            x + 10,
            cursor - 3,
            card_w - 20,
            6.6,
            color,
            string_width,
        )

    evidence_rows = (len(items) + 1) // 2
    cursor = start_y - evidence_rows * (card_h + gap) - 4
    canvas.setStrokeColor(color(COLORS["line"]))
    canvas.line(margin, cursor + 10, width - margin, cursor + 10)
    _section_label(canvas, margin, cursor, "ADVISORY NEXT STEPS", color)
    canvas.setFillColor(color(COLORS["ink"]))
    canvas.setFont("Times-Bold", 17)
    canvas.drawString(margin, cursor - 22, "What should happen next - and why")
    cursor -= 42

    for index, action in enumerate(analysis["recommended_actions"][:1], start=1):
        canvas.setFillColor(color("#f0f5f1"))
        canvas.roundRect(margin, cursor - 170, width - 2 * margin, 166, 8, fill=1, stroke=0)
        canvas.setFillColor(color(COLORS["skilled"]))
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(margin + 12, cursor - 21, f"{index}. RECOMMENDED ACTION - NOT EXECUTED")
        text_y = _wrapped_text(
            canvas,
            action["action"],
            margin + 12,
            cursor - 39,
            width - 2 * margin - 24,
            8.2,
            color,
            string_width,
        )
        text_y = _wrapped_text(
            canvas,
            action["rationale"],
            margin + 12,
            text_y - 2,
            width - 2 * margin - 24,
            7.2,
            color,
            string_width,
        )
        meta_w = (width - 2 * margin - 36) / 2
        left_meta = margin + 12
        right_meta = left_meta + meta_w + 12
        _section_label(canvas, left_meta, cursor - 93, "WHY NOW", color)
        _wrapped_text(canvas, action["why_now"], left_meta, cursor - 107, meta_w, 6.8, color, string_width)
        _section_label(canvas, right_meta, cursor - 93, "IMMEDIATE NEXT STEP", color)
        _wrapped_text(canvas, action["next_step"], right_meta, cursor - 107, meta_w, 6.8, color, string_width)
        _section_label(canvas, left_meta, cursor - 140, "EVIDENCE OF IMPROVEMENT", color)
        _wrapped_text(canvas, action["success_signal"], left_meta, cursor - 154, meta_w, 6.8, color, string_width)
        _section_label(canvas, right_meta, cursor - 140, "REVIEW HORIZON", color)
        _wrapped_text(canvas, action["review_horizon"], right_meta, cursor - 154, meta_w, 6.8, color, string_width)
        cursor -= 178

    _section_label(canvas, margin, cursor - 2, "CONCLUSION", color)
    _wrapped_text(
        canvas,
        analysis["narrative"]["conclusion"],
        margin,
        cursor - 20,
        width - 2 * margin,
        8,
        color,
        string_width,
    )
    _footer(canvas, view, width, color, page_number)
    canvas.showPage()


def _draw_action_page(
    canvas,
    view,
    pod,
    action,
    action_number,
    size,
    color,
    string_width,
    page_number: int,
) -> None:
    width, height = size
    margin = 44
    verdict = pod["analysis"]["verdict"]["classification"]
    canvas.setFillColor(color("#ffffff"))
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(color(COLORS["ink"]))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(margin, height - 42, f"{pod['pod_id'].upper()} | {verdict.upper()}")
    canvas.setFont("Times-Bold", 28)
    canvas.drawString(margin, height - 78, "Additional advisory action")
    canvas.setFillColor(color(COLORS["muted"]))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(margin, height - 110, "Continuation of the next steps shown in the interactive report.")

    top = height - 150
    canvas.setFillColor(color("#f0f5f1"))
    canvas.roundRect(margin, 210, width - 2 * margin, top - 210, 10, fill=1, stroke=0)
    canvas.setFillColor(color(COLORS["skilled"]))
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(margin + 16, top - 28, f"{action_number}. RECOMMENDED ACTION - NOT EXECUTED")
    cursor = _wrapped_text(
        canvas,
        action["action"],
        margin + 16,
        top - 55,
        width - 2 * margin - 32,
        11,
        color,
        string_width,
    )
    cursor = _wrapped_text(
        canvas,
        action["rationale"],
        margin + 16,
        cursor - 8,
        width - 2 * margin - 32,
        8.5,
        color,
        string_width,
    )
    blocks = [
        ("WHY NOW", action["why_now"]),
        ("IMMEDIATE NEXT STEP", action["next_step"]),
        ("EVIDENCE OF IMPROVEMENT", action["success_signal"]),
        ("REVIEW HORIZON", action["review_horizon"]),
    ]
    for label, text in blocks:
        cursor -= 14
        _section_label(canvas, margin + 16, cursor, label, color)
        cursor = _wrapped_text(
            canvas,
            text,
            margin + 16,
            cursor - 17,
            width - 2 * margin - 32,
            8,
            color,
            string_width,
        )

    _section_label(canvas, margin, 174, "CONCLUSION", color)
    _wrapped_text(
        canvas,
        pod["analysis"]["narrative"]["conclusion"],
        margin,
        154,
        width - 2 * margin,
        8.5,
        color,
        string_width,
    )
    _footer(canvas, view, width, color, page_number)
    canvas.showPage()


def _header(canvas, view, width, height, color) -> None:
    canvas.setFillColor(color(COLORS["ink"]))
    canvas.setFont("Times-Bold", 30)
    canvas.drawString(42, height - 48, "Pod risk review")
    canvas.setFillColor(color(COLORS["muted"]))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - 42, height - 35, view["report"]["run_id"])
    canvas.drawRightString(width - 42, height - 49, f"As of {view['report']['as_of']}")


def _footer(canvas, view, width, color, page: int) -> None:
    canvas.setFillColor(color(COLORS["muted"]))
    canvas.setFont("Helvetica", 6.5)
    canvas.drawString(42, 24, "Analyst recommendation only. No validator or governor action was executed.")
    canvas.drawRightString(width - 42, 24, f"{view['report']['run_id']} | Page {page}")


def _section_label(canvas, x, y, text, color) -> None:
    canvas.setFillColor(color(COLORS["muted"]))
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(x, y, text)


def _metric(pod: dict, name: str) -> str:
    metric = pod["risk_metrics"].get(name, {})
    value = metric.get("value_percent")
    return f"{value:+.1f}%" if isinstance(value, (int, float)) else "-"


def _risk_value(metric: dict) -> str:
    if isinstance(metric.get("value_percent"), (int, float)):
        return f"{metric['value_percent']:+.1f}%"
    if isinstance(metric.get("days"), (int, float)):
        return f"{metric['days']:g} days"
    if isinstance(metric.get("score"), (int, float)):
        return f"{metric['score']:.2f}"
    return "-"


def _ordinal(value: float) -> str:
    number = round(value)
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _wrapped_text(canvas, text, x, y, max_width, font_size, color, string_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if current and string_width(trial, "Helvetica", font_size) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    canvas.setFillColor(color(COLORS["ink"]))
    canvas.setFont("Helvetica", font_size)
    leading = font_size * 1.45
    for line in lines:
        canvas.drawString(x, y, line)
        y -= leading
    return y
