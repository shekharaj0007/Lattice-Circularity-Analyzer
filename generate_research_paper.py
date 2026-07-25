#!/usr/bin/env python3
"""
Research paper PDF: ML/physics process for predicting lattice EDM circularity
at any tool position. No website content. No handwritten ideation photos.
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
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Lattice_EDM_Circularity_Research_Paper.pdf"
FIGS = ROOT / "paper_figures"

PAGE_W, PAGE_H = letter
LEFT = RIGHT = 0.8 * inch
TOP = BOTTOM = 0.7 * inch


def make_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PaperTitle", parent=base["Title"], fontName="Times-Bold",
            fontSize=15, leading=18, alignment=TA_CENTER, spaceAfter=8,
        ),
        "authors": ParagraphStyle(
            "Authors", parent=base["Normal"], fontName="Times-Roman",
            fontSize=11, leading=14, alignment=TA_CENTER, spaceAfter=3,
        ),
        "affiliation": ParagraphStyle(
            "Affiliation", parent=base["Normal"], fontName="Times-Italic",
            fontSize=10, leading=12, alignment=TA_CENTER, spaceAfter=12,
        ),
        "heading1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName="Times-Bold",
            fontSize=12, leading=15, spaceBefore=11, spaceAfter=6,
        ),
        "heading2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName="Times-Bold",
            fontSize=11, leading=13, spaceBefore=8, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10.2, leading=13.4, alignment=TA_JUSTIFY,
            spaceAfter=7, firstLineIndent=14,
        ),
        "body_noindent": ParagraphStyle(
            "BodyNoIndent", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10.2, leading=13.4, alignment=TA_JUSTIFY, spaceAfter=7,
        ),
        "abstract": ParagraphStyle(
            "Abstract", parent=base["Normal"], fontName="Times-Roman",
            fontSize=9.8, leading=12.8, alignment=TA_JUSTIFY, spaceAfter=6,
            leftIndent=14, rightIndent=14,
        ),
        "caption": ParagraphStyle(
            "Caption", parent=base["Normal"], fontName="Times-Italic",
            fontSize=9, leading=11, alignment=TA_CENTER,
            spaceBefore=2, spaceAfter=9,
        ),
        "table_cell": ParagraphStyle(
            "TableCell", parent=base["Normal"], fontName="Times-Roman",
            fontSize=7.8, leading=9.5, alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "TableHeader", parent=base["Normal"], fontName="Times-Bold",
            fontSize=7.8, leading=9.5, alignment=TA_CENTER,
        ),
        "ref": ParagraphStyle(
            "Ref", parent=base["Normal"], fontName="Times-Roman",
            fontSize=8.8, leading=11, leftIndent=14, firstLineIndent=-14,
            spaceAfter=3, alignment=TA_LEFT,
        ),
        "keywords": ParagraphStyle(
            "Keywords", parent=base["Normal"], fontName="Times-Roman",
            fontSize=9.5, leading=12, leftIndent=14, rightIndent=14, spaceAfter=8,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10, leading=13, leftIndent=16, spaceAfter=3,
        ),
        "eq": ParagraphStyle(
            "Eq", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10.2, leading=13.4, alignment=TA_CENTER, spaceAfter=8, spaceBefore=2,
        ),
    }


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 9)
    canvas.drawCentredString(PAGE_W / 2, 0.4 * inch, str(canvas.getPageNumber()))
    canvas.restoreState()


def p(text, style):
    return Paragraph(text, style)


def fig(path: Path, width: float, caption: str, styles, max_h=3.0 * inch):
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


def two_figs(path_a, path_b, w, cap_a, cap_b, styles, max_h=2.6 * inch):
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
        colWidths=[w + 0.12 * inch, w + 0.12 * inch],
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
        ("FONTSIZE", (0, 0), (-1, -1), 7.8),
        ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#555555")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f4f6")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def build():
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter,
        leftMargin=LEFT, rightMargin=RIGHT, topMargin=TOP, bottomMargin=BOTTOM,
        title="Physics-Informed Machine Learning for Circularity Prediction in Lattice EDM",
        author="Lattice Circularity Analyzer Project",
    )
    story = []

    # Title
    story.append(p(
        "Physics-Informed Machine Learning for Predicting Supporting-Boundary "
        "Circularity at Any Tool Position in Micro-EDM of Metallic Lattices",
        styles["title"],
    ))
    story.append(p("Lattice Circularity Analyzer Project Team", styles["authors"]))
    story.append(p(
        "Research Paper — Ideation, Data Expansion, Training/Validation, and Position-Aware Prediction",
        styles["affiliation"],
    ))

    # Abstract
    story.append(p("Abstract", styles["heading1"]))
    story.append(p(
        "We present a physics-informed machine-learning method that predicts the circularity "
        "ratio of the supporting material boundary after micro-electrical discharge machining "
        "(EDM) of a metallic lattice, for <b>any tool landing position</b> (<i>x</i>,&nbsp;<i>y</i>) "
        "and any EDM recipe (peak current <i>I</i>, pulse-on time <i>T</i>, duty factor <i>D</i>). "
        "Only sixteen laboratory runs with SEM labels were available. From these, we (i) generated "
        "1,100 synthetic EDM points via a Gaussian Process posterior over the process inputs, and "
        "(ii) expanded each labeled run across a spatial landing grid by modulating SEM circularity "
        "with a geometry-risk penalty, producing hundreds of position-aware training rows. "
        "Dual Gradient Boosting regressors learn circularity (1–5) and supporting integrity; "
        "predictions are blended with EDM physics heuristics. Circularity ratio is reported as "
        "score/5. Leave-one-out and cross-validation guide trust. SEM evidence shows only "
        "Run&nbsp;4 (4&nbsp;A, 150&nbsp;µs, 80%) yields an intact circular supporting ring — "
        "the objective the models are trained to maximize.",
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
        "The scientific question is therefore: given (<i>I</i>, <i>T</i>, <i>D</i>, <i>x</i>, <i>y</i>), "
        "predict circularity ratio and whether the supporting boundary survives — even at positions "
        "never machined in the lab.",
        styles["body"],
    ))

    story.extend(fig(
        FIGS / "fig_geometry_ideation.png",
        5.6 * inch,
        "Fig. 1. Ideation schematic: 900 µm tool footprint on a 1500×1500 µm (3×3 cell) working area. "
        "Any landing position changes strut/node overlap and therefore circularity risk.",
        styles,
        max_h=3.3 * inch,
    ))

    # 2 Ideation / soul of method
    story.append(p("2. Ideation — The Working Mind of the Solution", styles["heading1"]))
    story.append(p(
        "The core idea is that circularity is not a property of EDM parameters alone. "
        "It is the <b>joint effect of process intensity and local lattice geometry under the tool</b>. "
        "Two landings with identical (<i>I</i>, <i>T</i>, <i>D</i>) can succeed at a pore center and "
        "fail near a strut because geometry risk changes. Conversely, even a favorable landing "
        "fails if current is too aggressive. That coupling is the “soul” of the method.",
        styles["body"],
    ))
    story.append(p("2.1 Three ideation principles", styles["heading2"]))
    story.append(p(
        "<b>Principle 1 — Objective from SEM, not metrology proxies.</b> "
        "Train to maximize supporting-boundary circularity judged from SEM, not to minimize "
        "Hole_Dev_Top/Bottom. Run&nbsp;5 looks “best” by deviation but destroys the ring; "
        "Run&nbsp;4 is the only SEM success.",
        styles["body"],
    ))
    story.append(p(
        "<b>Principle 2 — Geometry is a first-class feature.</b> "
        "Before any ML call, a lattice geometry engine computes how the tool footprint "
        "intersects nodes, pores, and struts at (<i>x</i>,&nbsp;<i>y</i>). Those quantities "
        "enter the feature vector beside EDM descriptors.",
        styles["body"],
    ))
    story.append(p(
        "<b>Principle 3 — Sparse lab truth + physics-structured expansion.</b> "
        "Sixteen runs cannot cover every (recipe × position). Expand data by (a) GP sampling "
        "in EDM space and (b) replaying each SEM label across a landing grid with geometry "
        "penalties that encode the physical belief “higher strut risk → lower circularity.”",
        styles["body"],
    ))

    story.extend(fig(
        FIGS / "fig_ml_pipeline.png",
        6.3 * inch,
        "Fig. 2. End-to-end ideation pipeline: sparse SEM truth → dual augmentation → "
        "physics features + EDM features → Gradient Boosting + heuristic blend → "
        "circularity ratio at any position.",
        styles,
        max_h=3.4 * inch,
    ))

    # 3 Physics
    story.append(p("3. Physics Used in the Predictor", styles["heading1"]))
    story.append(p("3.1 EDM process quantities", styles["heading2"]))
    story.append(p(
        "From machine settings we compute discharge energy and related intensity terms:",
        styles["body_noindent"],
    ))
    story.append(p(
        "<i>E</i> = <i>I</i> · <i>T</i> · (<i>D</i>/100), &nbsp;&nbsp; "
        "pulse-off ≈ <i>T</i>·(100−<i>D</i>)/<i>D</i>, &nbsp;&nbsp; "
        "<i>I</i>×<i>D</i>, &nbsp;&nbsp; <i>T</i>/<i>D</i>.",
        styles["eq"],
    ))
    story.append(p(
        "Physically, low current keeps a small plasma channel; long pulse-on spreads erosion "
        "more uniformly in the radial direction; high duty sustains continuous removal. "
        "Heuristics therefore reward <i>I</i> ≤ 5&nbsp;A, <i>T</i> ≥ 130&nbsp;µs, <i>D</i> ≥ 75%, "
        "and penalize <i>I</i> ≥ 8&nbsp;A (strut blasting).",
        styles["body"],
    ))

    story.append(p("3.2 Lattice geometry quantities at a landing", styles["heading2"]))
    story.append(p(
        "For tool center (<i>x</i>,&nbsp;<i>y</i>) on a 1500&nbsp;µm working area, the engine evaluates:",
        styles["body_noindent"],
    ))
    story.append(p("• minimum distance to nearest strut and nearest node center;", styles["bullet"]))
    story.append(p("• counts of nodes/pores inside the tool footprint;", styles["bullet"]))
    story.append(p("• strut intersection length inside the tool;", styles["bullet"]))
    story.append(p("• pore and node overlap fractions;", styles["bullet"]))
    story.append(p("• tool/pore ratio and a scalar <b>geometry risk</b> index:", styles["bullet"]))
    story.append(p(
        "geometry_risk = 0.5·strut_risk + 0.3·intersect_risk + 0.2·ratio_factor &nbsp;∈&nbsp;[0,1].",
        styles["eq"],
    ))
    story.append(p(
        "High geometry risk means the oversized tool is heavily chewing supporting ligaments — "
        "circularity is expected to fall even if the EDM recipe is gentle.",
        styles["body"],
    ))

    # 4 Data
    story.append(p("4. From 16 Experiments to a Trainable Dataset", styles["heading1"]))
    story.append(p(
        "Ground truth consists of sixteen EDM trials labeled from SEM on a 1–5 boundary-circularity "
        "scale plus a binary supporting-intact flag. Only Run&nbsp;4 scores 5 with an intact ring.",
        styles["body"],
    ))

    story.extend(fig(
        ROOT / "ACTUAL IMAGE OF THE 16 DATASETS .png",
        6.4 * inch,
        "Fig. 3. SEM montage of the sixteen experimental outcomes used as visual ground truth.",
        styles,
        max_h=3.1 * inch,
    ))

    header = [p(h, styles["table_header"]) for h in
              ["Run", "I", "T", "D", "Circ", "Intact", "Role"]]
    key = [
        ("4*", "4", "150", "80", "5", "Yes", "SEM success / target"),
        ("5", "6", "50", "64", "2", "No", "Best deviation, FAIL SEM"),
        ("1", "4", "50", "56", "1", "No", "Low-energy fail"),
        ("8", "6", "150", "72", "2", "No", "Asymmetric boundary"),
        ("13", "10", "50", "80", "1", "No", "High-current blast"),
        ("16", "10", "150", "56", "1", "No", "Irregular despite low Dev↓"),
    ]
    rows = [header] + [[p(c, styles["table_cell"]) for c in r] for r in key]
    story.append(styled_table(rows, [0.55*inch, 0.5*inch, 0.55*inch, 0.5*inch, 0.55*inch, 0.65*inch, 2.2*inch]))
    story.append(p("Table 1. Representative labeled runs (* = only SEM success).", styles["caption"]))

    story.append(p("4.1 Augmentation A — Gaussian Process synthetic EDM points (1,100)", styles["heading2"]))
    story.append(p(
        "A Gaussian Process was fit on the sixteen real (<i>I</i>, <i>T</i>, <i>D</i>) → response "
        "mappings (hole deviations / related process outputs). Sampling the GP posterior inside "
        "the experimental bounds generated <b>1,100 synthetic points</b> "
        "(file <font face='Courier'>synthetic_1100_points.csv</font>, source tag "
        "<font face='Courier'>GP_posterior</font>). These densify EDM-parameter space for "
        "exploratory Phase&nbsp;1 models. They are <b>not</b> new laboratory experiments; final "
        "SEM-anchored recommendations still privilege the sixteen real labels.",
        styles["body"],
    ))

    story.append(p("4.2 Augmentation B — Spatial expansion of SEM labels (position-aware rows)", styles["heading2"]))
    story.append(p(
        "To predict circularity at arbitrary (<i>x</i>,&nbsp;<i>y</i>), each of the 16 SEM labels "
        "is replayed on a discrete landing grid inside the valid tool-center bounds "
        "(step ≈ 150&nbsp;µm → 25 landings → <b>≈ 400 training rows</b>). For landing geometry "
        "features <i>g</i> and SEM circularity <i>c</i><sub>SEM</sub> of that run:",
        styles["body_noindent"],
    ))
    story.append(p(
        "<i>c</i><sub>train</sub> = clip( <i>c</i><sub>SEM</sub> − 2.5·geometry_risk(<i>g</i>) + edm_bonus(<i>I,T,D</i>) , 1, 5 ).",
        styles["eq"],
    ))
    story.append(p(
        "Here <i>edm_bonus</i> is +0.5 for gentle recipes (<i>I</i>≤5, <i>T</i>≥130, <i>D</i>≥75), "
        "−1.0 for <i>I</i>≥8, else 0. Supporting-integrity targets are set to 0 when current is "
        "high or geometry risk is large. This encodes the ideation that the same recipe degrades "
        "when the tool sits on dense strut intersections.",
        styles["body"],
    ))

    story.extend(fig(
        FIGS / "fig_data_expansion.png",
        6.2 * inch,
        "Fig. 4. Data-expansion path: 16 SEM-labeled runs → grid landings → geometry-modulated "
        "targets → models that generalize to unseen positions.",
        styles,
        max_h=2.4 * inch,
    ))

    # 5 ML
    story.append(p("5. Machine Learning Models, Training, Testing, Validation", styles["heading1"]))
    story.append(p("5.1 Feature vector (20 dimensions)", styles["heading2"]))
    story.append(p(
        "<b>EDM block (7):</b> <i>I</i>, <i>T</i>, <i>D</i>, energy <i>E</i>, pulse-off proxy, "
        "<i>I</i>×<i>D</i>, <i>T</i>/<i>D</i>. "
        "<b>Geometry block (13):</b> normalized (<i>x</i>,&nbsp;<i>y</i>), min distances to strut/node, "
        "nodes/pores inside tool, strut intersection length, pore/node overlap fractions, "
        "geometry risk, tool/pore ratio, working area, tool diameter.",
        styles["body"],
    ))

    story.append(p("5.2 Model architecture", styles["heading2"]))
    story.append(p(
        "Two supervised Gradient Boosting regressors (scikit-learn):",
        styles["body_noindent"],
    ))
    story.append(p(
        "• Circularity model: 120 estimators, max depth 4 → score ∈ [1, 5].",
        styles["bullet"],
    ))
    story.append(p(
        "• Supporting-integrity model: 80 estimators, max depth 3 → continuous score thresholded at 0.5.",
        styles["bullet"],
    ))
    story.append(p(
        "Phase&nbsp;1 (position-unknown) also uses a Gaussian Process Regressor with Matérn&nbsp;5/2 "
        "+ WhiteKernel on the 16 SEM circularity labels to search favorable (<i>I</i>, <i>T</i>, <i>D</i>) "
        "neighborhoods, and a polynomial Ridge model under leave-one-out cross-validation (LOOCV).",
        styles["body"],
    ))

    story.append(p("5.3 Train / test / validate protocol", styles["heading2"]))
    story.append(p(
        "<b>Training set (position-aware):</b> geometry-expanded rows from all 16 runs "
        "(≈400 samples at 150&nbsp;µm grid). Models are fit on the full expanded matrix and persisted.",
        styles["body"],
    ))
    story.append(p(
        "<b>Validation (small-n honest checks):</b> LOOCV on the 16 real SEM circularity labels "
        "for Phase&nbsp;1 Ridge/GP analysis yields MAE ≈ 1.02 on the 1–5 circularity scale. "
        "For exploratory 16+synthetic models, 5-fold cross-validated MAE on hole-deviation "
        "responses monitors overfitting in EDM space. Because the labeled set is tiny and "
        "unbalanced (one clear success), validation metrics are decision-support, not proof of "
        "industrial accuracy — SEM remains the ultimate test. Models are therefore always "
        "interpreted relative to the Run&nbsp;4 reference island rather than as absolute oracles.",
        styles["body"],
    ))
    story.append(p(
        "<b>Physics blend at inference (test-time regularization):</b> "
        "final circularity = (1−<i>w</i>)·ML + <i>w</i>·heuristic, where weight <i>w</i> grows "
        "when tool/pore sizes drift from the lab geometry (900&nbsp;µm / 235.6&nbsp;µm), "
        "capped near 0.7. When drift is large, supporting integrity also defers more to the "
        "heuristic. This prevents pure ML hallucination far from the training manifold while "
        "still letting Gradient Boosting dominate near the lab configuration.",
        styles["body"],
    ))
    story.append(p(
        "<b>What “testing” means here:</b> a held-out industrial test set does not exist yet "
        "(only one SEM success). Instead we (i) check LOOCV on the 16 labels, (ii) verify that "
        "grid predictions peak at low-risk pore-centered landings for Run&nbsp;4-like recipes, "
        "(iii) verify that high-current recipes stay FAIL across the grid, and (iv) confirm "
        "GP search returns candidates near 4&nbsp;A / 150&nbsp;µs / 80%. Those qualitative "
        "consistency tests are part of the validation story for sparse experimental ML.",
        styles["body"],
    ))

    ml_table = [
        [p(h, styles["table_header"]) for h in ["Stage", "Data", "Method", "Purpose"]],
        [p(c, styles["table_cell"]) for c in [
            "Phase 1 fit", "16 SEM labels", "GP (Matérn 5/2)", "Search robust (I,T,D)"]],
        [p(c, styles["table_cell"]) for c in [
            "Phase 1 CV", "16 runs LOOCV", "Polynomial Ridge", "Estimate circularity MAE"]],
        [p(c, styles["table_cell"]) for c in [
            "Synthetic densify", "GP posterior", "1,100 points", "Fill EDM input space"]],
        [p(c, styles["table_cell"]) for c in [
            "Spatial expand", "16 × ~25 landings", "Risk-modulated labels", "Teach position effect"]],
        [p(c, styles["table_cell"]) for c in [
            "Position model", "~400 rows / 20 feats", "GBR 120 + GBR 80", "Circularity & support"]],
        [p(c, styles["table_cell"]) for c in [
            "Inference", "Any (I,T,D,x,y)", "ML + heuristic blend", "Ratio = score/5"]],
    ]
    story.append(styled_table(ml_table, [1.15*inch, 1.45*inch, 1.55*inch, 1.85*inch]))
    story.append(p("Table 2. Training, validation, and inference stack.", styles["caption"]))

    # 6 How prediction works for any position
    story.append(p("6. Predicting Circularity Ratio for Any Position", styles["heading1"]))
    story.append(p(
        "Given a query (<i>I</i>, <i>T</i>, <i>D</i>, <i>x</i>, <i>y</i>):",
        styles["body_noindent"],
    ))
    story.append(p(
        "1. Run the geometry engine at (<i>x</i>,&nbsp;<i>y</i>) → risk and overlap features.",
        styles["bullet"],
    ))
    story.append(p(
        "2. Build the 20-D feature row (EDM + geometry).",
        styles["bullet"],
    ))
    story.append(p(
        "3. Predict ML circularity score <i>c</i><sub>ML</sub> ∈ [1,5] and supporting flag.",
        styles["bullet"],
    ))
    story.append(p(
        "4. Evaluate physics heuristic <i>c</i><sub>H</sub> from the gentle/aggressive rules and risk.",
        styles["bullet"],
    ))
    story.append(p(
        "5. Blend: <i>c</i> = (1−<i>w</i>)·<i>c</i><sub>ML</sub> + <i>w</i>·<i>c</i><sub>H</sub>.",
        styles["bullet"],
    ))
    story.append(p(
        "6. Report <b>circularity ratio</b> = <i>c</i> / 5. PASS if <i>c</i> ≥ 3.5 and supporting intact "
        "and geometry risk ≤ 0.55 (software gates used for engineering decisions).",
        styles["bullet"],
    ))
    story.append(p(
        "Scanning many (<i>x</i>,&nbsp;<i>y</i>) on a fine grid yields a spatial circularity field for "
        "fixed EDM settings — the practical realization of the ideation that position matters.",
        styles["body"],
    ))

    # 7 Results graphs
    story.append(p("7. Experimental Evidence and Learned Patterns", styles["heading1"]))
    story.append(p(
        "Graphs below are computed from the sixteen real runs and SEM labels. They justify "
        "why the training objective and heuristics look the way they do.",
        styles["body_noindent"],
    ))

    story.extend(two_figs(
        FIGS / "fig_circularity_by_run.png",
        FIGS / "fig_pass_fail_pie.png",
        3.3 * inch,
        "Fig. 5a. SEM circularity by run (only Run 4 passes).",
        "Fig. 5b. 1 PASS / 15 FAIL supporting-ring outcomes.",
        styles,
        max_h=2.55 * inch,
    ))

    story.extend(fig(
        FIGS / "fig_deviation_vs_circularity.png",
        6.0 * inch,
        "Fig. 6. Why the ML target is SEM circularity: Run 5 (low deviation) fails; "
        "Run 4 (higher deviation) is the only circular supporting boundary.",
        styles,
        max_h=3.1 * inch,
    ))

    story.extend(two_figs(
        FIGS / "fig_energy_vs_circularity.png",
        FIGS / "fig_current_pulse_heatmap.png",
        3.3 * inch,
        "Fig. 7a. Energy E=I·T·(D/100) vs SEM circularity.",
        "Fig. 7b. Mean circularity: Current × Pulse-on.",
        styles,
        max_h=2.55 * inch,
    ))

    story.append(p(
        "The learned neighborhood around Run&nbsp;4 — low <i>I</i>, long <i>T</i>, high <i>D</i> — "
        "matches both SEM truth and GP search recommendations (predicted circularity ≈ 4.6–4.9 "
        "near 3.6–4.8&nbsp;A / ≈150&nbsp;µs / ≈79–80%). Near-strut landings need slightly softer "
        "current (≈3.5&nbsp;A) because geometry risk is higher.",
        styles["body"],
    ))

    story.extend(fig(
        FIGS / "fig_final_recommendations.png",
        6.0 * inch,
        "Fig. 8. Final recommended parameter island from the SEM-informed analysis "
        "(Phase 1 unknown position; Phase 2 by zone).",
        styles,
        max_h=2.8 * inch,
    ))

    # 8 Final answers
    story.append(p("8. Final Answers Produced by This Process", styles["heading1"]))
    rec = [
        [p(h, styles["table_header"]) for h in ["Case", "Zone", "I (A)", "T (µs)", "D (%)", "Basis"]],
        [p(c, styles["table_cell"]) for c in ["Phase 1", "Unknown pos.", "4", "150", "80", "SEM Run 4 + GP"]],
        [p(c, styles["table_cell"]) for c in ["Phase 1 reject", "Dev-only opt.", "6", "50", "64", "Fails SEM ring"]],
        [p(c, styles["table_cell"]) for c in ["Phase 2", "Pore center", "4", "150", "80", "Low geom. risk"]],
        [p(c, styles["table_cell"]) for c in ["Phase 2", "Near strut", "3.5", "150", "78", "Higher geom. risk"]],
        [p(c, styles["table_cell"]) for c in ["Phase 2", "Near node", "3.5", "145", "76", "Corner overlap"]],
    ]
    story.append(styled_table(rec, [1.1*inch, 1.15*inch, 0.7*inch, 0.75*inch, 0.7*inch, 1.3*inch]))
    story.append(p("Table 3. Final parameter answers from the ML/physics process.", styles["caption"]))

    story.append(p(
        "Prediction outputs for any query position: circularity score (1–5), "
        "<b>circularity ratio = score/5</b>, supporting-material integrity, geometry risk, "
        "and PASS/FAIL against the thresholds score ≥ 3.5, ratio ≥ 0.70, supporting intact, "
        "risk ≤ 0.55.",
        styles["body"],
    ))

    # 9 Conclusion
    story.append(p("9. Conclusion", styles["heading1"]))
    story.append(p(
        "This work shows how a sparse SEM-labeled EDM campaign can still support "
        "position-aware circularity prediction. The ideation is simple but decisive: "
        "<b>couple process physics with lattice geometry, expand 16 labels through GP "
        "synthesis and risk-modulated spatial replay, train Gradient Boosting, and "
        "regularize with heuristics at inference</b>. That is how circularity ratio becomes "
        "computable for any tool position — not by collecting thousands of new SEM trials, "
        "but by teaching the model the geometry–process interaction that SEM revealed.",
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
        "[5] Lattice Circularity Analyzer Project (2026). Internal modules: "
        "<font face='Courier'>lattice_geometry_engine.py</font>, "
        "<font face='Courier'>circularity_predictor.py</font>, "
        "<font face='Courier'>phase1_model_actual.py</font>; datasets: "
        "<font face='Courier'>original_16_runs.csv</font>, "
        "<font face='Courier'>run_visual_labels.csv</font>, "
        "<font face='Courier'>synthetic_1100_points.csv</font>.",
    ]:
        story.append(p(r, styles["ref"]))

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    from pypdf import PdfReader
    n = len(PdfReader(str(OUTPUT)).pages)
    print(f"Saved: {OUTPUT} ({n} pages)")
    return n


if __name__ == "__main__":
    build()
