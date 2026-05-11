"""家长端：近 N 天膳食与任务周报 PDF（ReportLab + 内置 STSong-Light 中文）。"""
from __future__ import annotations

import html
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _esc(s) -> str:
    return html.escape(str(s) if s is not None else "", quote=False)


def _ensure_cjk_font() -> str:
    name = "STSong-Light"
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(name))
    return name


def build_parent_weekly_pdf(ctx: dict) -> bytes:
    """
    ctx 字段：
      title, child_label, period_label,
      daily_rows: [{date, meal_count, day_calories, avg_score}, ...],
      totals: {kcal, protein, carb, fat}, avg_daily_score,
      task_completed_count, diet_notes (可空)
      allergy_tags: [str], medical_tags: [str]
      intake: {calories_kcal_min, calories_kcal_max, protein_g_min, protein_g_max, notes} (可空)
    """
    font = _ensure_cjk_font()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "T",
        parent=styles["Heading1"],
        fontName=font,
        fontSize=18,
        leading=22,
        alignment=1,
        spaceAfter=6 * mm,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=13,
        leading=18,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
    )
    body = ParagraphStyle(
        "B",
        parent=styles["Normal"],
        fontName=font,
        fontSize=10,
        leading=14,
    )
    small = ParagraphStyle(
        "S",
        parent=styles["Normal"],
        fontName=font,
        fontSize=9,
        leading=12,
        textColor=colors.grey,
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=_esc(ctx.get("title", "周报")),
    )
    story = []

    story.append(Paragraph(_esc(ctx.get("title", "儿童膳食周报")), title_style))
    story.append(Paragraph(_esc(ctx.get("child_label", "")), body))
    story.append(Paragraph(_esc(ctx.get("period_label", "")), body))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("一、按日汇总", h2_style))
    hdr = ["日期", "餐次数", "当日热量(kcal)", "日均五色分"]
    data = [[_esc(h) for h in hdr]]
    for row in ctx.get("daily_rows") or []:
        data.append([
            _esc(row.get("date", "")),
            _esc(row.get("meal_count", 0)),
            _esc(f"{float(row.get('day_calories', 0) or 0):.0f}"),
            _esc(f"{float(row.get('avg_score', 0) or 0):.1f}"),
        ])
    t = Table(data, colWidths=[35 * mm, 22 * mm, 38 * mm, 35 * mm], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), font, 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3f2fd")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1565c0")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("二、周期合计", h2_style))
    tot = ctx.get("totals") or {}
    lines = [
        f"总热量：{float(tot.get('kcal', 0) or 0):.0f} kcal",
        f"蛋白质：{float(tot.get('protein', 0) or 0):.1f} g",
        f"碳水化合物：{float(tot.get('carb', 0) or 0):.1f} g",
        f"脂肪：{float(tot.get('fat', 0) or 0):.1f} g",
        f"日均五色营养分：{float(ctx.get('avg_daily_score', 0) or 0):.1f}",
        f"本周完成任务（已确认）：{int(ctx.get('task_completed_count', 0) or 0)} 次",
    ]
    for line in lines:
        story.append(Paragraph(_esc(line), body))

    intake = ctx.get("intake")
    if intake:
        story.append(Paragraph("三、每日建议摄入（参考范围）", h2_style))
        story.append(Paragraph(_esc(
            f"能量：{intake.get('calories_kcal_min')}–{intake.get('calories_kcal_max')} kcal/天；"
            f"蛋白质：{intake.get('protein_g_min')}–{intake.get('protein_g_max')} g/天"
        ), body))
        if intake.get("notes"):
            story.append(Paragraph(_esc(intake.get("notes")), small))

    allergy_tags = ctx.get("allergy_tags") or []
    medical_tags = ctx.get("medical_tags") or []
    if allergy_tags or medical_tags:
        story.append(Paragraph("四、过敏与医嘱标签（家长维护）", h2_style))
        if allergy_tags:
            story.append(Paragraph(_esc("过敏： " + "、".join([str(x) for x in allergy_tags])), body))
        if medical_tags:
            story.append(Paragraph(_esc("医嘱： " + "、".join([str(x) for x in medical_tags])), body))

    notes = (ctx.get("diet_notes") or "").strip()
    if notes:
        story.append(Paragraph("五、膳食备注（家长填写）", h2_style))
        story.append(Paragraph(_esc(notes), body))

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(_esc(ctx.get("footer", "")), small))

    doc.build(story)
    return buf.getvalue()
