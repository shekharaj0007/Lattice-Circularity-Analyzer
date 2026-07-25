#!/usr/bin/env python3
"""
Research paper PDF focused on ML/physics circularity prediction.
No Phase 1/Phase 2 framing. No website. No handwritten images.
Extra graphs inspired by EDM report chart types only.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Lattice_EDM_Circularity_Research_Paper.pdf"
FIGS = ROOT / "paper_figures"

PAGE_W, PAGE_H = letter
LEFT = RIGHT = 0.78 * inch
TOP = BOTTOM = 0.68 * inch


def make_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PaperTitle", parent=base["Title"], fontName="Times-Bold",
            fontSize=14.5, leading=18, alignment=TA_CENTER, spaceAfter=7,
        ),
        "authors": ParagraphStyle(
            "Authors", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10.5, leading=13, alignment=TA_CENTER, spaceAfter=3,
        ),
        "affiliation": ParagraphStyle(
            "Affiliation", parent=base["Normal"], fontName="Times-Italic",
            fontSize=9.5, leading=12, alignment=TA_CENTER, spaceAfter=10,
        ),
        "heading1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName="Times-Bold",
            fontSize=11.5, leading=14, spaceBefore=10, spaceAfter=5,
        ),
        "heading2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName="Times-Bold",
            fontSize=10.5, leading=13, spaceBefore=7, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10, leading=13.2, alignment=TA_JUSTIFY,
            spaceAfter=6, firstLineIndent=12,
        ),
        "body_noindent": ParagraphStyle(
            "BodyNoIndent", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10, leading=13.2, alignment=TA_JUSTIFY, spaceAfter=6,
        ),
        "abstract": ParagraphStyle(
            "Abstract", parent=base["Normal"], fontName="Times-Roman",
            fontSize=9.5, leading=12.4, alignment=TA_JUSTIFY, spaceAfter=5,
            leftIndent=12, rightIndent=12,
        ),
        "caption": ParagraphStyle(
            "Caption", parent=base["Normal"], fontName="Times-Italic",
            fontSize=8.5, leading=10.5, alignment=TA_CENTER,
            spaceBefore=2, spaceAfter=8,
        ),
        "table_cell": ParagraphStyle(
            "TableCell", parent=base["Normal"], fontName="Times-Roman",
            fontSize=7.5, leading=9.2, alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "TableHeader", parent=base["Normal"], fontName="Times-Bold",
            fontSize=7.5, leading=9.2, alignment=TA_CENTER,
        ),
        "ref": ParagraphStyle(
            "Ref", parent=base["Normal"], fontName="Times-Roman",
            fontSize=8.5, leading=10.5, leftIndent=12, firstLineIndent=-12,
            spaceAfter=2, alignment=TA_LEFT,
        ),
        "keywords": ParagraphStyle(
            "Keywords", parent=base["Normal"], fontName="Times-Roman",
            fontSize=9.3, leading=12, leftIndent=12, rightIndent=12, spaceAfter=7,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["Normal"], fontName="Times-Roman",
            fontSize=9.8, leading=12.5, leftIndent=14, spaceAfter=2,
        ),
        "eq": ParagraphStyle(
            "Eq", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10, leading=13, alignment=TA_CENTER, spaceAfter=7, spaceBefore=2,
        ),
    }


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 9)
    canvas.drawCentredString(PAGE_W / 2, 0.38 * inch, str(canvas.getPageNumber()))
    canvas.restoreState()


def p(text, style):
    return Paragraph(text, style)


def fig(path: Path, width: float, caption: str, styles, max_h=2.85 * inch):
    if not path.exists():
        return [p(f"[Missing figure: {path.name}]", styles["caption"])]
    from PIL import Image as PILImage

    with PILImage.open(path) as im:
        aspect = im.size[1] / float(im.size[0])
    img = Image(str(path), width=width, height=width * aspect)
    img.hAlign = "CENTER"
    if img.drawHeight > max_h:
        s = max_h / img.drawHeight
        img.drawWidth *= s
        img.drawHeight *= s
    return [KeepTogether([img, p(caption, styles["caption"])])]


def two_figs(path_a, path_b, w, cap_a, cap_b, styles, max_h=2.45 * inch):
    from PIL import Image as PILImage

    def one(path, width):
        if not path.exists():
            return p(f"[Missing: {path.name}]", styles["caption"])
        with PILImage.open(path) as im:
            aspect = im.size[1] / float(im.size[0])
        img = Image(str(path), width=width, height=width * aspect)
        if img.drawHeight > max_h:
            s = max_h / img.drawHeight
            img.drawWidth *= s
            img.drawHeight *= s
        return img

    t = Table(
        [[one(path_a, w), one(path_b, w)],
         [p(cap_a, styles["caption"]), p(cap_b, styles["caption"])]],
        colWidths=[w + 0.1 * inch, w + 0.1 * inch],
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return [t]


def styled_table(data, col_widths):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#555555")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f4f6")]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return t


def build():
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter,
        leftMargin=LEFT, rightMargin=RIGHT, topMargin=TOP, bottomMargin=BOTTOM,
        title="Physics-Informed ML for Circularity Prediction in Lattice EDM",
        author="Lattice Circularity Analyzer Project",
    )
    story = []

    story.append(p(
        "Physics-Informed Machine Learning for Predicting Supporting-Boundary "
        "Circularity at Any Tool Position in Micro-EDM of Metallic Lattices",
        styles["title"],
    ))
    story.append(p("Lattice Circularity Analyzer Project Team", styles["authors"]))
    story.append(p(
        "Research Paper — Ideation, Data Expansion, Training/Validation, Position-Aware Prediction",
        styles["affiliation"],
    ))

    story.append(p("Abstract", styles["heading1"]))
    story.append(p(
        "We present a physics-informed machine-learning method that predicts the circularity "
        "ratio of the supporting material boundary after micro-EDM of a metallic lattice, for "
        "<b>any tool landing position</b> (<i>x</i>,&nbsp;<i>y</i>) and any EDM recipe "
        "(peak current <i>I</i>, pulse-on time <i>T</i>, duty factor <i>D</i>). Only sixteen "
        "laboratory runs with SEM labels were available. From these we generated 1,100 synthetic "
        "EDM points via a Gaussian Process posterior, and expanded each labeled run across a "
        "spatial landing grid by modulating SEM circularity with a geometry-risk penalty "
        "(≈400 position-aware training rows). Dual Gradient Boosting regressors learn circularity "
        "(1–5) and supporting integrity; predictions are blended with EDM physics heuristics. "
        "Circularity ratio = score/5. SEM evidence shows only Run&nbsp;4 (4&nbsp;A, 150&nbsp;µs, 80%) "
        "yields an intact circular supporting ring — the objective the models maximize.",
        styles["abstract"],
    ))
    story.append(p(
        "<b>Keywords:</b> micro-EDM; lattice structures; circularity ratio; Gaussian process; "
        "gradient boosting; physics-informed ML; data augmentation; SEM validation",
        styles["keywords"],
    ))

    # 1 Problem
    story.append(p("1. Problem Definition", styles["heading1"]))
    story.append(p(
        "A metallic lattice has square unit cells of side 500&nbsp;µm. Pore and node diameters "
        "equal <i>x</i> = 500√2 / 3 ≈ 235.6&nbsp;µm. The EDM tool tip is 900&nbsp;µm "
        "(tool/pore = 3.82), so the electrode always overlaps pores, nodes, and supporting struts "
        "together. Success means a nearly circular open region with a <b>continuous supporting "
        "ring</b>; nodes may be destroyed. Hole-deviation numbers alone are insufficient: among "
        "sixteen SEM-validated trials, only Run&nbsp;4 produced the desired ring.",
        styles["body"],
    ))
    story.append(p(
        "The question answered here: given (<i>I</i>, <i>T</i>, <i>D</i>, <i>x</i>, <i>y</i>), "
        "predict circularity ratio and whether the supporting boundary survives — even at "
        "positions never machined in the lab.",
        styles["body"],
    ))
    story.extend(fig(
        FIGS / "fig_geometry_ideation.png",
        5.4 * inch,
        "Fig. 1. Tool footprint (900 µm) on a 1500×1500 µm working area. Landing position "
        "changes strut/node overlap and circularity risk.",
        styles, max_h=3.0 * inch,
    ))

    # 2 Ideation
    story.append(p("2. Ideation — How Circularity Can Be Predicted Anywhere", styles["heading1"]))
    story.append(p(
        "Circularity is not a property of EDM parameters alone. It is the <b>joint effect of "
        "process intensity and local lattice geometry under the tool</b>. Identical "
        "(<i>I</i>, <i>T</i>, <i>D</i>) can succeed at a pore center and fail near a strut. "
        "That coupling is the working idea of the solution.",
        styles["body"],
    ))
    story.append(p(
        "<b>Idea 1 — Train on SEM boundary truth.</b> Do not minimize Hole_Dev_Top/Bottom. "
        "Maximize supporting-boundary circularity from SEM. Run&nbsp;5 looks best by deviation "
        "but destroys the ring; Run&nbsp;4 is the only SEM success.",
        styles["body"],
    ))
    story.append(p(
        "<b>Idea 2 — Geometry is a first-class feature.</b> Before ML, a lattice engine computes "
        "how the tool intersects nodes, pores, and struts at (<i>x</i>,&nbsp;<i>y</i>).",
        styles["body"],
    ))
    story.append(p(
        "<b>Idea 3 — Expand sparse lab truth with physics structure.</b> Densify EDM space with "
        "GP sampling, and replay each SEM label across a landing grid with geometry penalties.",
        styles["body"],
    ))
    story.extend(fig(
        FIGS / "fig_ml_pipeline.png",
        6.2 * inch,
        "Fig. 2. Prediction pipeline: SEM truth → dual augmentation → physics + EDM features → "
        "Gradient Boosting + heuristic blend → circularity ratio at any position.",
        styles, max_h=3.15 * inch,
    ))

    # 3 Experimental evidence graphs (inspired by report chart types)
    story.append(p("3. Experimental Evidence — Graphs from the 16 Runs", styles["heading1"]))
    story.append(p(
        "All charts below are computed from the laboratory table and SEM labels. They show why "
        "deviation-only ranking misleads and why the ML target must be SEM circularity.",
        styles["body_noindent"],
    ))

    story.extend(fig(
        ROOT / "ACTUAL IMAGE OF THE 16 DATASETS .png",
        6.3 * inch,
        "Fig. 3. SEM montage of all 16 experimental outcomes (visual ground truth).",
        styles, max_h=2.9 * inch,
    ))

    story.extend(two_figs(
        FIGS / "fig_circularity_by_run.png",
        FIGS / "fig_pass_fail_pie.png",
        3.25 * inch,
        "Fig. 4a. SEM circularity by run (green = PASS).",
        "Fig. 4b. 1 PASS / 15 FAIL supporting-ring outcomes.",
        styles,
    ))

    story.extend(fig(
        FIGS / "fig_top_bottom_deviation.png",
        6.2 * inch,
        "Fig. 5. Top vs bottom hole deviation for all 16 runs. Large top–bottom gaps indicate taper "
        "(asymmetric plasma erosion).",
        styles, max_h=2.75 * inch,
    ))

    story.extend(two_figs(
        FIGS / "fig_asymmetry.png",
        FIGS / "fig_dev_score_ranking.png",
        3.25 * inch,
        "Fig. 6a. Absolute asymmetry |Dev_Top − Dev_Bot|.",
        "Fig. 6b. Deviation-score ranking (wrong metric): Run 4 near worst, yet only SEM PASS.",
        styles,
    ))

    story.extend(fig(
        FIGS / "fig_deviation_vs_circularity.png",
        5.9 * inch,
        "Fig. 7. Paradox scatter: SEM circularity ratio vs mean deviation. The SEM PASS (Run 4) "
        "does not sit in the low-deviation corner.",
        styles, max_h=2.95 * inch,
    ))

    story.extend(two_figs(
        FIGS / "fig_param_effects_dev.png",
        FIGS / "fig_duty_effects_dev.png",
        3.25 * inch,
        "Fig. 8a. Mean top/bottom deviation by current and pulse-on.",
        "Fig. 8b. Duty-factor effect on top/bottom deviation.",
        styles,
    ))

    story.extend(two_figs(
        FIGS / "fig_energy_vs_circularity.png",
        FIGS / "fig_current_pulse_heatmap.png",
        3.25 * inch,
        "Fig. 9a. Discharge energy vs SEM circularity.",
        "Fig. 9b. Mean circularity heatmap: Current × Pulse-on.",
        styles,
    ))

    story.extend(fig(
        FIGS / "fig_mrr_twr.png",
        6.2 * inch,
        "Fig. 10. Process responses: volume removal rate and tool wear rate across the 16 runs "
        "(context for intensity, not the success metric).",
        styles, max_h=2.55 * inch,
    ))

    # 4 Physics
    story.append(p("4. Physics Used in the Predictor", styles["heading1"]))
    story.append(p(
        "EDM descriptors: discharge energy <i>E</i> = <i>I</i>·<i>T</i>·(<i>D</i>/100), "
        "pulse-off ≈ <i>T</i>·(100−<i>D</i>)/<i>D</i>, <i>I</i>×<i>D</i>, <i>T</i>/<i>D</i>. "
        "Heuristics reward low current / long pulse / high duty and penalize <i>I</i> ≥ 8&nbsp;A.",
        styles["body"],
    ))
    story.append(p(
        "At landing (<i>x</i>,&nbsp;<i>y</i>) the geometry engine computes min distances to strut/node, "
        "nodes/pores inside the tool, strut intersection length, pore/node overlap fractions, and",
        styles["body_noindent"],
    ))
    story.append(p(
        "geometry_risk = 0.5·strut_risk + 0.3·intersect_risk + 0.2·ratio_factor &nbsp;∈&nbsp;[0,1].",
        styles["eq"],
    ))

    # 5 Data expansion
    story.append(p("5. From 16 Experiments to a Trainable Dataset", styles["heading1"]))
    story.append(p(
        "<b>Augmentation A — GP synthetic EDM points (1,100).</b> A Gaussian Process fit on the "
        "sixteen real (<i>I</i>, <i>T</i>, <i>D</i>) → response mappings was sampled in-bounds to "
        "produce <font face='Courier'>synthetic_1100_points.csv</font> (source "
        "<font face='Courier'>GP_posterior</font>). These densify process space; they are not new "
        "lab experiments.",
        styles["body"],
    ))
    story.append(p(
        "<b>Augmentation B — Spatial label replay (~400 rows).</b> Each SEM label is applied on a "
        "landing grid (≈25 positions at 150&nbsp;µm step inside valid tool-center bounds):",
        styles["body_noindent"],
    ))
    story.append(p(
        "<i>c</i><sub>train</sub> = clip( <i>c</i><sub>SEM</sub> − 2.5·geometry_risk + edm_bonus , 1, 5 ).",
        styles["eq"],
    ))
    story.append(p(
        "Gentle recipes get a small bonus; <i>I</i> ≥ 8 gets a penalty. This teaches that the same "
        "recipe degrades when the tool sits on dense strut intersections.",
        styles["body"],
    ))
    story.extend(fig(
        FIGS / "fig_data_expansion.png",
        6.1 * inch,
        "Fig. 11. Data-expansion path from 16 SEM-labeled runs to position-aware training rows.",
        styles, max_h=2.2 * inch,
    ))

    # 6 ML train/validate
    story.append(p("6. Machine Learning — Train, Test, Validate", styles["heading1"]))
    story.append(p(
        "<b>Features (20-D):</b> EDM block (<i>I</i>, <i>T</i>, <i>D</i>, energy, pulse-off, "
        "<i>I</i>×<i>D</i>, <i>T</i>/<i>D</i>) + geometry block (normalized <i>x,y</i>, distances, "
        "counts, overlaps, geometry risk, tool/pore ratio, working area, tool diameter).",
        styles["body"],
    ))
    story.append(p(
        "<b>Models:</b> GradientBoostingRegressor — 120 trees (circularity 1–5) and 80 trees "
        "(supporting integrity, threshold 0.5). Separately, a Matérn&nbsp;5/2 Gaussian Process on "
        "the 16 SEM labels searches favorable (<i>I</i>, <i>T</i>, <i>D</i>) neighborhoods; "
        "polynomial Ridge under leave-one-out CV estimates small-n MAE (≈1.02 / 5).",
        styles["body"],
    ))
    story.append(p(
        "<b>Validation practice for sparse SEM data:</b> (i) LOOCV on 16 labels; "
        "(ii) 5-fold CV on exploratory 16+synthetic deviation models; "
        "(iii) qualitative grid checks — Run&nbsp;4-like recipes peak at low-risk pore centers; "
        "high-current recipes stay FAIL; GP candidates cluster near 4&nbsp;A / 150&nbsp;µs / 80%. "
        "SEM remains the ultimate test.",
        styles["body"],
    ))
    story.append(p(
        "<b>Inference blend:</b> <i>c</i> = (1−<i>w</i>)·<i>c</i><sub>ML</sub> + <i>w</i>·<i>c</i><sub>H</sub>, "
        "with <i>w</i> rising when tool/pore sizes drift from the lab geometry. "
        "<b>Circularity ratio</b> = <i>c</i>/5. PASS if <i>c</i> ≥ 3.5, supporting intact, risk ≤ 0.55.",
        styles["body"],
    ))

    ml_table = [
        [p(h, styles["table_header"]) for h in ["Stage", "Data", "Method", "Purpose"]],
        [p(c, styles["table_cell"]) for c in ["SEM fit", "16 labels", "GP Matérn 5/2", "Search robust (I,T,D)"]],
        [p(c, styles["table_cell"]) for c in ["Small-n CV", "16-run LOOCV", "Poly Ridge", "Circularity MAE"]],
        [p(c, styles["table_cell"]) for c in ["Densify EDM", "GP posterior", "1,100 points", "Fill input space"]],
        [p(c, styles["table_cell"]) for c in ["Spatial expand", "16 × ~25 landings", "Risk-modulated labels", "Teach position effect"]],
        [p(c, styles["table_cell"]) for c in ["Position model", "~400 × 20 feats", "GBR 120 + GBR 80", "Score & support"]],
        [p(c, styles["table_cell"]) for c in ["Inference", "Any (I,T,D,x,y)", "ML + heuristic", "Ratio = score/5"]],
    ]
    story.append(styled_table(ml_table, [1.15*inch, 1.4*inch, 1.55*inch, 1.8*inch]))
    story.append(p("Table 1. Training, validation, and inference stack.", styles["caption"]))

    # 7 Any-position steps
    story.append(p("7. Predicting Circularity Ratio for Any Position", styles["heading1"]))
    story.append(p("1. Geometry engine at (<i>x</i>,&nbsp;<i>y</i>) → risk and overlap features.", styles["bullet"]))
    story.append(p("2. Build 20-D feature row (EDM + geometry).", styles["bullet"]))
    story.append(p("3. Predict ML circularity score and supporting flag.", styles["bullet"]))
    story.append(p("4. Evaluate physics heuristic from gentle/aggressive rules + risk.", styles["bullet"]))
    story.append(p("5. Blend ML with heuristic; report ratio = score/5 and PASS/FAIL.", styles["bullet"]))
    story.append(p(
        "Scanning many landings for fixed EDM settings produces a spatial circularity field — "
        "the practical realization that position matters.",
        styles["body"],
    ))

    # 8 Final answers (no Phase wording)
    story.append(p("8. Final Recommended Parameters", styles["heading1"]))
    story.extend(fig(
        FIGS / "fig_final_recommendations.png",
        5.9 * inch,
        "Fig. 12. Recommended EDM settings by landing zone (unknown position uses the robust "
        "Run 4 island; near-strut/node landings soften current).",
        styles, max_h=2.55 * inch,
    ))
    rec = [
        [p(h, styles["table_header"]) for h in ["Landing situation", "I (A)", "T (µs)", "D (%)", "Basis"]],
        [p(c, styles["table_cell"]) for c in ["Position unknown (robust)", "4", "150", "80", "SEM Run 4 + GP"]],
        [p(c, styles["table_cell"]) for c in ["Pore center", "4", "150", "80", "Low geometry risk"]],
        [p(c, styles["table_cell"]) for c in ["Mid pore", "4", "148", "79", "Near-center"]],
        [p(c, styles["table_cell"]) for c in ["Near strut", "3.5", "150", "78", "Higher geometry risk"]],
        [p(c, styles["table_cell"]) for c in ["Near node / corner", "3.5", "145", "76", "Corner overlap"]],
        [p(c, styles["table_cell"]) for c in ["Deviation-only (reject)", "6", "50", "64", "Fails SEM ring"]],
    ]
    story.append(styled_table(rec, [1.85*inch, 0.7*inch, 0.75*inch, 0.7*inch, 1.6*inch]))
    story.append(p("Table 2. Final parameter answers from the ML/physics process.", styles["caption"]))

    story.append(p("9. Conclusion", styles["heading1"]))
    story.append(p(
        "Sparse SEM-labeled EDM data can still support position-aware circularity prediction if "
        "we couple process physics with lattice geometry, expand 16 labels through GP synthesis "
        "and risk-modulated spatial replay, train Gradient Boosting, and regularize with heuristics "
        "at inference. Circularity ratio becomes computable for any tool position by teaching the "
        "geometry–process interaction that SEM revealed — not by collecting thousands of new trials.",
        styles["body"],
    ))

    story.append(p("References", styles["heading1"]))
    for r in [
        "[1] Ho, K. H., &amp; Newman, S. T. (2003). State of the art electrical discharge machining (EDM). "
        "<i>Int. J. Machine Tools &amp; Manufacture</i>.",
        "[2] Kunieda, M., et al. (2005). Advancing EDM through fundamental insight into the process. "
        "<i>CIRP Annals</i>.",
        "[3] Rasmussen, C. E., &amp; Williams, C. K. I. (2006). <i>Gaussian Processes for Machine Learning</i>. MIT Press.",
        "[4] Friedman, J. H. (2001). Greedy function approximation: A gradient boosting machine. "
        "<i>Annals of Statistics</i>.",
        "[5] Project datasets &amp; modules (2026): "
        "<font face='Courier'>original_16_runs.csv</font>, "
        "<font face='Courier'>run_visual_labels.csv</font>, "
        "<font face='Courier'>synthetic_1100_points.csv</font>; "
        "<font face='Courier'>lattice_geometry_engine.py</font>, "
        "<font face='Courier'>circularity_predictor.py</font>.",
    ]:
        story.append(p(r, styles["ref"]))

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    from pypdf import PdfReader
    n = len(PdfReader(str(OUTPUT)).pages)
    print(f"Saved: {OUTPUT} ({n} pages)")
    # Guard: no Phase 1/2 wording
    text = "\n".join((pg.extract_text() or "") for pg in PdfReader(str(OUTPUT)).pages)
    for bad in ["Phase 1", "Phase 2", "PHASE 1", "PHASE 2"]:
        if bad in text:
            print("WARNING: found forbidden phrase:", bad)
    print("Phase wording check done.")
    return n


if __name__ == "__main__":
    build()
