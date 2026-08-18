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

    # 6 ML detailed
    story.append(p("6. Machine Learning in Detail", styles["heading1"]))
    story.append(p(
        "This section explains exactly what is learned, from which labels, with which algorithms, "
        "how models are validated on only sixteen SEM trials, and how a prediction is formed for "
        "an unseen landing position.",
        styles["body_noindent"],
    ))

    story.append(p("6.1 Learning targets (what the models try to predict)", styles["heading2"]))
    story.append(p(
        "Two supervised targets are used. <b>Target A — boundary circularity score</b> "
        "<i>c</i> ∈ {1,2,3,4,5} from SEM judgment of the supporting ring (Run&nbsp;4 = 5; most "
        "failures = 1–2). At inference we also report <b>circularity ratio</b> = <i>c</i>/5 "
        "(so 3.5/5 → 0.70). <b>Target B — supporting integrity</b> "
        "<i>s</i> ∈ {0,1}: whether the black ring is continuous. Hole deviation is "
        "<i>not</i> the training target for the position-aware system, because minimizing it "
        "recovers Run&nbsp;5 and destroys struts.",
        styles["body"],
    ))

    story.append(p("6.2 Feature vector (20 dimensions)", styles["heading2"]))
    story.append(p(
        "Every training row and every query builds the same 20-D vector "
        "<b>X = [X<sub>EDM</sub> | X<sub>geom</sub>]</b>.",
        styles["body_noindent"],
    ))
    story.append(p(
        "<b>EDM block (7 features):</b> raw settings <i>I</i>, <i>T</i>, <i>D</i>; "
        "discharge energy <i>E</i> = <i>I</i>·<i>T</i>·(<i>D</i>/100); "
        "pulse-off proxy <i>T</i>·(100−<i>D</i>)/<i>D</i>; interaction terms <i>I</i>·<i>D</i> and "
        "<i>T</i>/<i>D</i>. These terms let trees split on intensity and on “gentle vs punchy” "
        "delivery, not only on raw ampere or microsecond values.",
        styles["body"],
    ))
    story.append(p(
        "<b>Geometry block (13 features):</b> normalized landing "
        "<i>x</i>/<i>W</i>, <i>y</i>/<i>W</i> (<i>W</i> = 1500&nbsp;µm); "
        "min distance to strut; min distance to node center; count of nodes inside the tool; "
        "count of pore centers inside the tool; strut intersection length inside the footprint; "
        "pore overlap fraction; node overlap fraction; scalar geometry risk; tool/pore ratio; "
        "working area; tool diameter. This block is why the model can answer “same recipe, "
        "different (<i>x</i>,&nbsp;<i>y</i>)”.",
        styles["body"],
    ))

    feat_table = [
        [p(h, styles["table_header"]) for h in ["#", "Feature", "Type", "Role in learning"]],
        [p(c, styles["table_cell"]) for c in ["1–3", "I, T, D", "EDM raw", "Primary process controls"]],
        [p(c, styles["table_cell"]) for c in ["4", "Energy E", "EDM derived", "Total spark intensity"]],
        [p(c, styles["table_cell"]) for c in ["5", "Pulse-off proxy", "EDM derived", "Flush / recovery time"]],
        [p(c, styles["table_cell"]) for c in ["6–7", "I·D, T/D", "EDM interaction", "Duty-coupled effects"]],
        [p(c, styles["table_cell"]) for c in ["8–9", "x/W, y/W", "Geometry", "Where the tool lands"]],
        [p(c, styles["table_cell"]) for c in ["10–11", "Dist. strut/node", "Geometry", "Clearance to ligaments"]],
        [p(c, styles["table_cell"]) for c in ["12–13", "Nodes/pores in tool", "Geometry", "How much cell is engulfed"]],
        [p(c, styles["table_cell"]) for c in ["14–16", "Strut len, overlaps", "Geometry", "Damage exposure"]],
        [p(c, styles["table_cell"]) for c in ["17", "Geometry risk", "Geometry", "Compressed risk index"]],
        [p(c, styles["table_cell"]) for c in ["18–20", "Ratio, W, tool Ø", "Config", "Scale / overfill context"]],
    ]
    story.append(styled_table(feat_table, [0.55*inch, 1.45*inch, 1.1*inch, 2.5*inch]))
    story.append(p("Table 1. Full 20-D feature vector used by Gradient Boosting.", styles["caption"]))

    story.append(p("6.3 Building supervised labels from only 16 SEM runs", styles["heading2"]))
    story.append(p(
        "Lab SEM gives one circularity and one integrity flag per EDM recipe — not per landing. "
        "To supervise position dependence we <b>replay</b> each recipe on a landing grid "
        "(step 150&nbsp;µm inside valid tool-center bounds → 25 landings → 16×25 = 400 rows):",
        styles["body_noindent"],
    ))
    story.append(p(
        "<i>c</i><sub>train</sub>(run,<i>x,y</i>) = clip( <i>c</i><sub>SEM</sub>(run) "
        "− 2.5·geometry_risk(<i>x,y</i>) + edm_bonus(<i>I,T,D</i>) , 1, 5 )",
        styles["eq"],
    ))
    story.append(p(
        "where edm_bonus = +0.5 if (<i>I</i>≤5, <i>T</i>≥130, <i>D</i>≥75), −1.0 if <i>I</i>≥8, "
        "else 0. Supporting label <i>s</i><sub>train</sub> = 1 only if the SEM flag is intact "
        "<i>and</i> geometry_risk &lt; 0.6 <i>and</i> <i>I</i> &lt; 8; for near-Run&nbsp;4 recipes "
        "(<i>I</i>≤4.5, <i>T</i>≥140, <i>D</i>≥78) we allow <i>s</i><sub>train</sub> = "
        "max(s, 1 − geometry_risk). This is physics-informed label propagation: the SEM score "
        "is the anchor; geometry risk lowers the target when the tool sits on struts.",
        styles["body"],
    ))
    story.append(p(
        "Separately, a Gaussian Process posterior over the 16 real (<i>I</i>, <i>T</i>, <i>D</i>) "
        "points produces 1,100 synthetic EDM rows used to densify process-parameter space for "
        "exploratory models. Those synthetics are tagged <font face='Courier'>GP_posterior</font> "
        "and are never treated as new SEM ground truth.",
        styles["body"],
    ))

    story.append(p("6.4 Algorithms and hyperparameters", styles["heading2"]))
    story.append(p(
        "<b>(A) Position-aware predictors — Gradient Boosting.</b> "
        "Two <font face='Courier'>GradientBoostingRegressor</font> models (scikit-learn) are "
        "trained on the 400×20 matrix:",
        styles["body_noindent"],
    ))
    story.append(p(
        "• Circularity model: <i>n_estimators</i>=120, <i>max_depth</i>=4, "
        "<i>random_state</i>=42 → continuous score clipped to [1,5].",
        styles["bullet"],
    ))
    story.append(p(
        "• Supporting model: <i>n_estimators</i>=80, <i>max_depth</i>=3, "
        "<i>random_state</i>=42 → score thresholded at 0.5 for intact/not.",
        styles["bullet"],
    ))
    story.append(p(
        "Gradient boosting was chosen because the feature set mixes continuous physics quantities "
        "with nonlinear interactions (e.g., high current only becomes catastrophic when strut "
        "intersection is large), and tree ensembles handle mixed-scale features without heavy "
        "normalization. Depth is kept shallow (3–4) to limit overfitting on a few hundred "
        "physically correlated rows derived from only 16 recipes.",
        styles["body"],
    ))
    story.append(p(
        "<b>(B) Recipe search on SEM labels — Gaussian Process.</b> "
        "A <font face='Courier'>GaussianProcessRegressor</font> with kernel "
        "Matérn(<i>ν</i>=2.5) + WhiteKernel(noise=0.3), <i>normalize_y</i>=True, is fit on the "
        "16 points (<i>I</i>, <i>T</i>, <i>D</i>) → SEM circularity. About 3,000 random candidates "
        "are drawn (half concentrated near the gentle island 3.5–5.5&nbsp;A / 120–150&nbsp;µs / "
        "75–80%, half over the full DOE box). Candidates are ranked by "
        "<i>μ</i> + 0.15·<i>σ</i> (mean plus mild exploration). This recovers the Run&nbsp;4 "
        "neighborhood (≈3.6–4.8&nbsp;A, ≈150&nbsp;µs, ≈79–80%) with predicted scores ≈4.6–4.9.",
        styles["body"],
    ))
    story.append(p(
        "<b>(C) Small-n baseline — polynomial Ridge LOOCV.</b> "
        "Degree-2 polynomial features of (<i>I</i>, <i>T</i>, <i>D</i>) with Ridge(<i>α</i>=0.5) "
        "under leave-one-out cross-validation measure how predictable SEM circularity is from "
        "recipe alone. Result: LOO MAE ≈ 1.02 on the 1–5 scale — usable as a guide, not as "
        "high-precision metrology.",
        styles["body"],
    ))

    story.append(p("6.5 Training procedure", styles["heading2"]))
    story.append(p(
        "1. Load <font face='Courier'>original_16_runs.csv</font> and "
        "<font face='Courier'>run_visual_labels.csv</font>.",
        styles["bullet"],
    ))
    story.append(p(
        "2. Enumerate landing grid with <font face='Courier'>grid_positions(step_um=150)</font>.",
        styles["bullet"],
    ))
    story.append(p(
        "3. For each (run, landing): run <font face='Courier'>analyze_position</font>, "
        "build 20-D <b>X</b>, compute <i>c</i><sub>train</sub> and <i>s</i><sub>train</sub>.",
        styles["bullet"],
    ))
    story.append(p(
        "4. Fit both Gradient Boosting models with <font face='Courier'>.fit(X, y)</font>.",
        styles["bullet"],
    ))
    story.append(p(
        "5. Persist bundle "
        "{circularity, supporting, n_features=20} via joblib for reuse at inference.",
        styles["bullet"],
    ))
    story.append(p(
        "No random train/test split of landings is used as the primary protocol, because landings "
        "from the same run are strongly dependent. Instead, honesty comes from LOOCV on the 16 "
        "independent SEM recipes plus physical consistency checks (next subsection).",
        styles["body"],
    ))

    story.append(p("6.6 Validation and testing strategy", styles["heading2"]))
    story.append(p(
        "<b>Quantitative:</b> Leave-one-out CV on the 16 SEM circularity labels (Ridge/polynomial) "
        "→ MAE ≈ 1.02. Exploratory models that include the 1,100 GP synthetics use 5-fold "
        "cross-validated MAE on hole-deviation responses to watch overfitting in EDM space only.",
        styles["body"],
    ))
    story.append(p(
        "<b>Qualitative consistency tests (critical for n=16):</b> "
        "(i) for Run&nbsp;4-like recipes, predicted circularity must peak at low geometry-risk "
        "pore-centered landings; "
        "(ii) for <i>I</i> ≥ 8&nbsp;A, predictions must stay FAIL across the grid; "
        "(iii) GP search must place top candidates near 4&nbsp;A / 150&nbsp;µs / 80%; "
        "(iv) deviation-minimizing recipes must not outrank SEM-successful ones when the "
        "circularity target is used. SEM images remain the final acceptance test.",
        styles["body"],
    ))

    story.append(p("6.7 Physics heuristic and ML–physics blending at inference", styles["heading2"]))
    story.append(p(
        "A transparent heuristic score <i>c</i><sub>H</sub> encodes SEM lessons without trees: "
        "base ≈ 4.2–4.5 for gentle recipes (<i>I</i>≤5, long <i>T</i>, high <i>D</i>); "
        "base ≈ 1.8–2.2 for aggressive recipes; then "
        "<i>c</i><sub>H</sub> ← clip(<i>c</i><sub>H</sub> − 2.2·geometry_risk "
        "+ 0.3·[dist_strut&gt;150], 1, 5). Supporting heuristic requires gentle EDM and "
        "geometry_risk ≤ 0.55 (stricter if intersection length is large); <i>I</i> ≥ 8 always fails.",
        styles["body"],
    ))
    story.append(p(
        "Final score blends ML and heuristic:",
        styles["body_noindent"],
    ))
    story.append(p(
        "<i>c</i> = (1−<i>w</i>) · <i>c</i><sub>ML</sub> + <i>w</i> · <i>c</i><sub>H</sub>, &nbsp;&nbsp; "
        "<i>w</i> = min(0.7, 0.35 + 0.15·drift),",
        styles["eq"],
    ))
    story.append(p(
        "where drift = |toolØ − 900|/900 + |poreØ − 235.6|/235.6. Near the lab geometry, ML "
        "dominates; when the user changes tool/pore sizes far from training, the heuristic weight "
        "rises so the system does not confidently hallucinate. Supporting integrity similarly "
        "requires heuristic agreement when <i>w</i> is large. "
        "<b>Circularity ratio</b> = <i>c</i>/5. "
        "PASS if <i>c</i> ≥ 3.5, supporting intact, and geometry risk ≤ 0.55.",
        styles["body"],
    ))

    ml_table = [
        [p(h, styles["table_header"]) for h in ["Stage", "Data", "Method", "Purpose"]],
        [p(c, styles["table_cell"]) for c in ["Recipe search", "16 SEM labels", "GP Matérn 5/2", "Find robust (I,T,D)"]],
        [p(c, styles["table_cell"]) for c in ["Small-n CV", "16-run LOOCV", "Poly Ridge α=0.5", "MAE ≈ 1.02 / 5"]],
        [p(c, styles["table_cell"]) for c in ["Densify EDM", "GP posterior", "1,100 synthetics", "Fill input space"]],
        [p(c, styles["table_cell"]) for c in ["Spatial labels", "16 × 25 landings", "Risk-modulated SEM", "Teach (x,y) effect"]],
        [p(c, styles["table_cell"]) for c in ["Fit models", "400 × 20 features", "GBR 120 + GBR 80", "Score & support"]],
        [p(c, styles["table_cell"]) for c in ["Inference", "Any (I,T,D,x,y)", "ML + heuristic blend", "Ratio = score/5"]],
    ]
    story.append(styled_table(ml_table, [1.15*inch, 1.35*inch, 1.55*inch, 1.55*inch]))
    story.append(p("Table 2. End-to-end ML stack from labels to inference.", styles["caption"]))

    # 7 Any-position steps
    story.append(p("7. Predicting Circularity Ratio for Any Position", styles["heading1"]))
    story.append(p(
        "For a query (<i>I</i>, <i>T</i>, <i>D</i>, <i>x</i>, <i>y</i>) the runtime path is:",
        styles["body_noindent"],
    ))
    story.append(p(
        "1. <b>Geometry pass:</b> <font face='Courier'>analyze_position(x,y)</font> computes "
        "distances, overlaps, intersection length, and geometry_risk.",
        styles["bullet"],
    ))
    story.append(p(
        "2. <b>Feature build:</b> concatenate 7 EDM features with 13 geometry features → 20-D row.",
        styles["bullet"],
    ))
    story.append(p(
        "3. <b>ML forward:</b> circularity GBR → <i>c</i><sub>ML</sub>; supporting GBR → "
        "<i>s</i><sub>ML</sub> (threshold 0.5).",
        styles["bullet"],
    ))
    story.append(p(
        "4. <b>Heuristic forward:</b> evaluate <i>c</i><sub>H</sub> and <i>s</i><sub>H</sub> from "
        "the gentle/aggressive rules and risk.",
        styles["bullet"],
    ))
    story.append(p(
        "5. <b>Blend:</b> compute drift-based weight <i>w</i>; "
        "<i>c</i> = (1−<i>w</i>)<i>c</i><sub>ML</sub> + <i>w</i><i>c</i><sub>H</sub>; "
        "combine supporting flags.",
        styles["bullet"],
    ))
    story.append(p(
        "6. <b>Report:</b> score <i>c</i>, circularity ratio <i>c</i>/5, supporting OK, "
        "geometry risk, PASS/FAIL. Repeating steps 1–6 on a fine (<i>x</i>,&nbsp;<i>y</i>) grid "
        "yields a spatial circularity field for fixed EDM settings.",
        styles["bullet"],
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
    story.append(p("Table 3. Final parameter answers from the ML/physics process.", styles["caption"]))

    story.append(p("9. Conclusion", styles["heading1"]))
    story.append(p(
        "Sparse SEM-labeled EDM data can still support position-aware circularity prediction if "
        "we couple process physics with lattice geometry, expand 16 labels through GP synthesis "
        "and risk-modulated spatial replay, train Gradient Boosting on a 20-D EDM+geometry feature "
        "vector, validate with LOOCV plus physical consistency checks, and regularize with "
        "heuristics at inference. Circularity ratio becomes computable for any tool position by "
        "teaching the geometry–process interaction that SEM revealed — not by collecting thousands "
        "of new trials.",
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
