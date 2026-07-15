import os
import json
from datetime import date, timedelta
from flask import Flask, request, jsonify
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfgen import canvas as rl_canvas

app = Flask(__name__)

OUTPUT_DIR = r"C:\Users\SOORYA S S\.n8n-files"

MEAL_ORDER = [
    "06:00 AM On Waking Up",
    "08:00 AM Breakfast",
    "10:30 AM Morning Snack",
    "01:00 PM Lunch",
    "04:00 PM Pre Workout",
    "06:00 PM Post Workout",
    "08:00 PM Dinner",
    "09:30 PM Bed Time",
]

# ── Professional Black & White Palette ───────────────────────────────────────
PRIMARY      = colors.HexColor("#000000")
PRIMARY_DARK = colors.HexColor("#000000")
ACCENT       = colors.HexColor("#000000")
LIGHT_BG     = colors.HexColor("#FFFFFF")
PALE_BG      = colors.HexColor("#FFFFFF")
WHITE        = colors.white
DARK_GREY    = colors.HexColor("#000000")
MID_GREY     = colors.HexColor("#333333")
LIGHT_GREY   = colors.HexColor("#FFFFFF")
BORDER       = colors.HexColor("#000000")

# ── Font names (Times New Roman family) ──────────────────────────────────────
FONT_REGULAR = "Times-Roman"
FONT_BOLD    = "Times-Bold"
FONT_ITALIC  = "Times-Italic"


def _style(name, font=FONT_REGULAR, size=10, leading=14,
           alignment=TA_LEFT, color=DARK_GREY,
           space_before=0, space_after=0, bold=False):
    return ParagraphStyle(
        name,
        fontName=FONT_BOLD if bold else font,
        fontSize=size,
        leading=leading,
        alignment=alignment,
        textColor=color,
        spaceBefore=space_before,
        spaceAfter=space_after,
        wordWrap='LTR',
    )


def _base_table_style():
    return [
        # Header row — white background, bold black text, no fill
        ("FONTNAME",       (0, 0), (-1, 0),  FONT_BOLD),
        ("FONTSIZE",       (0, 0), (-1, 0),  9),
        ("BACKGROUND",     (0, 0), (-1, 0),  colors.white),
        ("TEXTCOLOR",      (0, 0), (-1, 0),  colors.black),
        ("ALIGN",          (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        # Body rows — white background, black text
        ("FONTNAME",       (0, 1), (-1, -1), FONT_REGULAR),
        ("FONTSIZE",       (0, 1), (-1, -1), 8.5),
        ("BACKGROUND",     (0, 1), (-1, -1), colors.white),
        ("TEXTCOLOR",      (0, 1), (-1, -1), colors.black),
        ("ALIGN",          (0, 1), (-1, -1), "LEFT"),
        # Black grid
        ("GRID",           (0, 0), (-1, -1), 0.5, colors.black),
        ("LINEABOVE",      (0, 0), (-1, 0),  1.0, colors.black),
        ("LINEBELOW",      (0, -1), (-1, -1), 0.8, colors.black),
        # Padding
        ("TOPPADDING",     (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
    ]


def _section_title(text, story, styles):
    story.append(Spacer(1, 12))
    story.append(Paragraph(text, styles["section_title"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.black, spaceAfter=6))


# ── Watermark callback ────────────────────────────────────────────────────────
def _watermark_canvas_maker(watermark_text="NutrifyMyDiet"):
    from reportlab.pdfgen.canvas import Canvas

    class WatermarkCanvas(Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._watermark_text = watermark_text

        def showPage(self):
            self._draw_watermark()
            super().showPage()

        def save(self):
            self._draw_watermark()
            super().save()

        def _draw_watermark(self):
            self.saveState()
            page_width, page_height = letter
            self.setFont(FONT_BOLD, 52)
            self.setFillColor(colors.black, alpha=0.10)
            self.translate(page_width / 2, page_height / 2)
            self.rotate(45)
            text_width = self.stringWidth(self._watermark_text, FONT_BOLD, 52)
            self.drawString(-text_width / 2, 0, self._watermark_text)
            self.restoreState()

    return WatermarkCanvas


def generate_nutrition_pdf(data: dict, pdf_path: str) -> None:
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    page_w = letter[0] - 1.5 * inch

    styles = {
        "client_name": _style(
            "client_name", size=24, leading=30,
            alignment=TA_LEFT, color=PRIMARY_DARK,
            space_after=2, bold=True,
        ),
        "subtitle": _style(
            "subtitle", size=10, leading=14,
            alignment=TA_CENTER, color=MID_GREY,
            space_after=4,
        ),
        "section_title": _style(
            "section_title", size=11, leading=14,
            color=PRIMARY_DARK, space_before=2, space_after=2, bold=True,
        ),
        "body": _style("body", size=9.5, leading=14, color=DARK_GREY),
        "note_text": _style(
            "note_text", size=9.5, leading=15,
            alignment=TA_JUSTIFY, color=MID_GREY,
        ),
        "disclaimer_title": _style(
            "disclaimer_title", size=10, leading=13,
            color=PRIMARY_DARK, space_before=6, bold=True,
        ),
        "disclaimer_body": _style(
            "disclaimer_body", size=8.5, leading=12.5,
            alignment=TA_JUSTIFY, color=MID_GREY,
        ),
        "empty_msg": _style(
            "empty_msg", size=9, leading=14,
            alignment=TA_CENTER, color=MID_GREY,
        ),
        "cell_wrap": _style(
            "cell_wrap", size=8.5, leading=12,
            alignment=TA_LEFT, color=DARK_GREY,
        ),
        "cell_meal_header": _style(
            "cell_meal_header", font=FONT_BOLD, size=8.5, leading=12,
            alignment=TA_LEFT, color=colors.black,
        ),
    }

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # HEADER BANNER
    # ══════════════════════════════════════════════════════════════════════════
    header_data = [[
        Paragraph(data.get("client_name", ""), styles["client_name"]),
        Paragraph("Prepared by<br/><b>NutrifyMyDiet</b>", ParagraphStyle(
            "hdr_right", fontName=FONT_REGULAR, fontSize=9, leading=13,
            alignment=TA_RIGHT, textColor=MID_GREY,
        )),
    ]]
    header_table = Table(header_data, colWidths=[page_w * 0.65, page_w * 0.35])
    header_table.setStyle(TableStyle([
        ("VALIGN",         (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING",    (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 0),
        ("TOPPADDING",     (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2.5, color=PRIMARY, spaceBefore=4, spaceAfter=10))

    # ══════════════════════════════════════════════════════════════════════════
    # NUTRITION SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    _section_title("NUTRITION SUMMARY", story, styles)

    cal   = data.get("total_calories", "—")
    carbs = data.get("total_carbs", "—")
    prot  = data.get("total_protein", "—")
    fat   = data.get("total_fat", "—")

    def _metric_cell(label, value):
        return Paragraph(
            f'<font size="8" color="#000000"><i>{label}</i></font><br/>'
            f'<font size="13"><b>{value}</b></font>',
            ParagraphStyle("mc", fontName=FONT_REGULAR, fontSize=13, leading=18,
                           alignment=TA_CENTER, textColor=PRIMARY_DARK),
        )

    summary_data = [[
        _metric_cell("Total Calories", cal),
        _metric_cell("Total Carbs", carbs),
        _metric_cell("Total Protein", prot),
        _metric_cell("Total Fat", fat),
    ]]
    col_w = page_w / 4
    summary_table = Table(summary_data, colWidths=[col_w] * 4, rowHeights=[50])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.white),
        ("BOX",           (0, 0), (-1, -1), 1.5, colors.black),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.black),
        ("TEXTCOLOR",     (0, 0), (-1, -1), colors.black),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)

    # ══════════════════════════════════════════════════════════════════════════
    # APPROVED NUTRITION PLAN
    # ══════════════════════════════════════════════════════════════════════════
    _section_title("APPROVED NUTRITION PLAN", story, styles)

    col_time = page_w * 0.22
    col_food = page_w * 0.46
    col_cal  = page_w * 0.13
    col_qty  = page_w * 0.19

    def _wrap(text, st="cell_wrap"):
        return Paragraph(str(text), styles[st])

    approved_plan = data.get("approved_plan", {})
    meal_table_data = [[
        _wrap("Time"),
        _wrap("Food Item"),
        _wrap("Calories"),
        _wrap("Quantity"),
    ]]
    meal_table_cmds = list(_base_table_style())
    meal_table_cmds += [("ALIGN", (0, 0), (-1, 0), "CENTER")]

    row_idx = 1
    for meal_time in MEAL_ORDER:
        items = approved_plan.get(meal_time)
        if not items:
            continue

        meal_table_data.append([
            Paragraph(meal_time, styles["cell_meal_header"]), "", "", ""
        ])
        meal_table_cmds += [
            ("BACKGROUND",    (0, row_idx), (-1, row_idx), colors.white),
            ("TEXTCOLOR",     (0, row_idx), (-1, row_idx), colors.black),
            ("FONTNAME",      (0, row_idx), (-1, row_idx), FONT_BOLD),
            ("FONTSIZE",      (0, row_idx), (-1, row_idx), 8.5),
            ("SPAN",          (0, row_idx), (-1, row_idx)),
            ("ALIGN",         (0, row_idx), (-1, row_idx), "LEFT"),
            ("TOPPADDING",    (0, row_idx), (-1, row_idx), 5),
            ("BOTTOMPADDING", (0, row_idx), (-1, row_idx), 5),
        ]
        row_idx += 1

        for item in items:
            meal_table_data.append([
                Paragraph("", styles["cell_wrap"]),
                _wrap(item.get("name", "")),
                _wrap(str(item.get("calories", ""))),
                _wrap(item.get("quantity", "")),
            ])
            row_idx += 1

    meal_table = Table(
        meal_table_data,
        colWidths=[col_time, col_food, col_cal, col_qty],
        repeatRows=1,
    )
    meal_table.setStyle(TableStyle(meal_table_cmds))
    story.append(meal_table)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2 – Supplements + Recipes on same page
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    _section_title("SUPPLEMENTS", story, styles)
    supplements = data.get("supplements", [])
    if supplements:
        supp_data = [["Name", "Dosage"]]
        for s in supplements:
            supp_data.append([
                _wrap(s.get("name", "")),
                _wrap(s.get("dosage", "")),
            ])
        supp_table = Table(supp_data, colWidths=[page_w * 0.55, page_w * 0.45])
        supp_table.setStyle(TableStyle(_base_table_style()))
        story.append(supp_table)
    else:
        story.append(Paragraph("No supplements prescribed.", styles["empty_msg"]))

    _section_title("RECIPES", story, styles)
    recipes = data.get("recipes", [])
    if recipes:
        recipe_data = [["Recipe Name", "Ingredients", "Instructions"]]
        for r in recipes:
            recipe_data.append([
                _wrap(r.get("name", "")),
                _wrap(r.get("ingredients", "")),
                _wrap(r.get("instructions", "")),
            ])
        recipe_table = Table(
            recipe_data,
            colWidths=[page_w * 0.22, page_w * 0.36, page_w * 0.42],
        )
        recipe_table.setStyle(TableStyle(_base_table_style()))
        story.append(recipe_table)
    else:
        story.append(Paragraph("No recipes available.", styles["empty_msg"]))

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3 – Notes, Dates, Disclaimer (no trailing PageBreak)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    _section_title("NOTES FROM THE NUTRITIONIST", story, styles)
    notes = data.get("nutritionist_notes", "").strip()
    story.append(Paragraph(notes if notes else "No additional notes.", styles["note_text"]))

    # ── PROGRAM DURATION ─────────────────────────────────────────────────────
    # Change 1: End date now calculated from plan_duration_days instead of
    # a hardcoded one-month offset. Start date remains today's date.
    _section_title("PROGRAM DURATION", story, styles)
    start_date = date.today()
    plan_duration_days = int(data.get("plan_duration_days", 30))   # NEW: read from payload
    end_date = start_date + timedelta(days=plan_duration_days - 1)      # NEW: dynamic end date
    duration_data = [
        ["Start Date", "End Date"],
        [start_date.strftime("%d %B %Y"), end_date.strftime("%d %B %Y")],
    ]
    duration_table = Table(duration_data, colWidths=[page_w * 0.5, page_w * 0.5])
    dur_style = list(_base_table_style())
    dur_style += [
        ("FONTNAME",  (0, 1), (-1, 1), FONT_BOLD),
        ("FONTSIZE",  (0, 1), (-1, 1), 11),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.black),
        ("ALIGN",     (0, 1), (-1, 1), "CENTER"),
    ]
    duration_table.setStyle(TableStyle(dur_style))
    story.append(duration_table)

    # ── APPOINTMENTS ─────────────────────────────────────────────────────────
    # Change 2: New section displaying scheduled meetings from the payload.
    _section_title("APPOINTMENTS", story, styles)
    meetings = data.get("meetings", [])
    if meetings:
        appt_data = [["Date", "Time", "Meeting Link"]]
        for m in meetings:
            # Parse ISO date string (YYYY-MM-DD) and reformat to DD Mon YYYY
            raw_date = m.get("meeting_date", "")
            try:
                parsed_date = date.fromisoformat(raw_date)
                display_date = parsed_date.strftime("%d %b %Y")
            except (ValueError, TypeError):
                display_date = raw_date   # fall back to raw value if unparseable

            appt_data.append([
                _wrap(display_date),
                _wrap(m.get("meeting_time", "")),
                _wrap(m.get("meet_link", "")),
            ])
        appt_table = Table(
            appt_data,
            colWidths=[page_w * 0.22, page_w * 0.18, page_w * 0.60],
        )
        appt_table.setStyle(TableStyle(_base_table_style()))
        story.append(appt_table)
    else:
        story.append(Paragraph("No appointments scheduled.", styles["empty_msg"]))

    _section_title("PLEASE NOTE", story, styles)
    story.append(Paragraph(
        "The Nutrition Program will not be extended beyond the program end date. "
        "The extension shall be considered only in case of a medical emergency.",
        styles["note_text"],
    ))

    story.append(Spacer(1, 14))
    story.append(Paragraph("DISCLAIMER", styles["disclaimer_title"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=6))

    disclaimer_paragraphs = [
        ("General Information Only",
         "The nutrition plan provided herein has been prepared solely for the named "
         "individual based on information supplied at the time of consultation. It is "
         "intended as general dietary guidance and does not constitute medical advice, "
         "diagnosis, or treatment."),
        ("Professional Supervision",
         "This plan should be followed under the supervision of a qualified healthcare "
         "professional. If you experience any adverse effects, discomfort, or unexpected "
         "changes in your health while following this programme, please discontinue "
         "immediately and consult your physician."),
        ("Individual Variation",
         "Nutritional needs vary among individuals depending on age, sex, health status, "
         "activity level, medications, and other factors. The calorie and macronutrient "
         "targets provided are estimates and may need to be adjusted over time."),
        ("Allergies & Intolerances",
         "It is the responsibility of the client to inform their nutritionist of all known "
         "food allergies, intolerances, or dietary restrictions. The practitioner accepts no "
         "liability for adverse reactions arising from undisclosed allergies or intolerances."),
        ("Not a Substitute for Medical Treatment",
         "This nutrition plan is not a substitute for professional medical advice or treatment "
         "for any condition, disease, or disorder. Persons with existing medical conditions "
         "should seek specific medical guidance before commencing any dietary change."),
        ("Confidentiality",
         "This document is prepared exclusively for the named client and must not be shared, "
         "reproduced, or distributed without the prior written consent of the issuing nutritionist."),
        ("Limitation of Liability",
         "To the fullest extent permitted by applicable law, the nutritionist and associated "
         "practitioners shall not be liable for any direct, indirect, incidental, or "
         "consequential loss or damage arising from reliance on the information contained in "
         "this plan. By following this programme, the client acknowledges and accepts these terms."),
    ]

    for label, content in disclaimer_paragraphs:
        story.append(Paragraph(
            f"<b>{label}:</b> {content}",
            styles["disclaimer_body"],
        ))
        story.append(Spacer(1, 5))

    # ── Build with watermark canvas ───────────────────────────────────────────
    doc.build(story, canvasmaker=_watermark_canvas_maker("NutrifyMyDiet"))


@app.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"success": False, "error": "No JSON body received."}), 400

        if isinstance(data, list):
            data = data[0]

        plan_id = data.get("plan_id", "unknown")
        client_name = data.get("client_name", "Client")

# Remove invalid filename characters
        safe_name = "".join(c for c in client_name if c not in r'<>:"/\|?*')

        filename = f"{safe_name} - Nutrition Plan - {plan_id}.pdf"

        pdf_path = os.path.join(OUTPUT_DIR, filename)

        generate_nutrition_pdf(data, pdf_path)

        return jsonify({
    "success": True,
    "pdf_path": os.path.abspath(pdf_path),
    "email": data.get("email"),
    "client_name": data.get("client_name"),
    "plan_id": plan_id
}), 200

    except Exception as exc:
        import traceback
        return jsonify({"success": False, "error": str(exc), "trace": traceback.format_exc()}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)