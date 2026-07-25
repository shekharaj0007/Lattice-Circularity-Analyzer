#!/usr/bin/env python3
"""Generate a 7–10 page research paper PDF for the Lattice EDM Circularity project."""

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
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Lattice_EDM_Circularity_Research_Paper.pdf"

PAGE_W, PAGE_H = letter
LEFT = RIGHT = 0.85 * inch
TOP = BOTTOM = 0.75 * inch


def make_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "PaperTitle",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "authors": ParagraphStyle(
            "Authors",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "affiliation": ParagraphStyle(
            "Affiliation",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=10,
            leading=12,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "heading1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=12,
            leading=15,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#1a1a1a"),
        ),
        "heading2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Times-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10.5,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            firstLineIndent=14,
        ),
        "body_noindent": ParagraphStyle(
            "BodyNoIndent",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10.5,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "abstract": ParagraphStyle(
            "Abstract",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=13,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            leftIndent=18,
            rightIndent=18,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=12,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
        ),
        "ref": ParagraphStyle(
            "Ref",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=9.5,
            leading=12,
            leftIndent=18,
            firstLineIndent=-18,
            spaceAfter=4,
            alignment=TA_LEFT,
        ),
        "keywords": ParagraphStyle(
            "Keywords",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=13,
            leftIndent=18,
            rightIndent=18,
            spaceAfter=10,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=9,
            alignment=TA_CENTER,
        ),
    }
    return styles


def add_page_number(canvas, doc):
    canvas.saveState()
    page = canvas.getPageNumber()
    canvas.setFont("Times-Roman", 9)
    canvas.drawCentredString(PAGE_W / 2, 0.45 * inch, str(page))
    canvas.restoreState()


def p(text: str, style):
    return Paragraph(text, style)


def maybe_image(path: Path, width: float, caption: str, styles):
    if not path.exists():
        return [p(f"[Figure unavailable: {path.name}]", styles["caption"])]
    img = Image(str(path), width=width, height=width * 0.62)
    img.hAlign = "CENTER"
    # Keep aspect closer for wide SEM panels
    try:
        from PIL import Image as PILImage

        with PILImage.open(path) as im:
            w, h = im.size
            aspect = h / float(w)
            img = Image(str(path), width=width, height=width * aspect)
            img.hAlign = "CENTER"
            # Cap height so pages stay balanced
            if img.drawHeight > 3.2 * inch:
                scale = (3.2 * inch) / img.drawHeight
                img.drawWidth *= scale
                img.drawHeight *= scale
    except Exception:
        pass
    return [KeepTogether([img, p(caption, styles["caption"])])]


def styled_table(data, col_widths):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#555555")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f4f6")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def build():
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=LEFT,
        rightMargin=RIGHT,
        topMargin=TOP,
        bottomMargin=BOTTOM,
        title="Machine Learning–Guided Circularity Prediction for EDM of Metallic Lattice Structures",
        author="Lattice Circularity Analyzer Project",
    )

    story = []

    # --- Title block ---
    story.append(
        p(
            "Machine Learning–Guided Circularity Prediction for "
            "Electrical Discharge Machining of Metallic Lattice Structures",
            styles["title"],
        )
    )
    story.append(p("Lattice Circularity Analyzer (LatticeFlow) Project Team", styles["authors"]))
    story.append(
        p(
            "Department of Mechanical / Manufacturing Engineering &amp; Applied Machine Learning<br/>"
            "Project Report — Research Paper Format",
            styles["affiliation"],
        )
    )

    # --- Abstract ---
    story.append(p("Abstract", styles["heading1"]))
    story.append(
        p(
            "Metallic lattice structures used in biomedical implants and lightweight aerospace components "
            "require post-processing to form circular through-holes with intact supporting rings. "
            "This work addresses micro-electrical discharge machining (EDM) of a lattice whose open pore "
            "(235.6&nbsp;µm) is substantially smaller than the electrode tip (900&nbsp;µm), giving a tool-to-pore "
            "ratio of 3.82. Sixteen laboratory trials with scanning electron microscopy (SEM) validation "
            "show that only one parameter set — peak current 4&nbsp;A, pulse-on time 150&nbsp;µs, duty factor 80% — "
            "produces a continuous, nearly circular supporting boundary. Hole-deviation metrics alone "
            "incorrectly favor a destructive setting (6&nbsp;A, 50&nbsp;µs, 64%). We formulate a two-phase "
            "optimization problem (unknown vs. known tool landing position), train Gaussian Process and "
            "Gradient Boosting models on SEM-labeled circularity, and deploy an interactive web system "
            "that predicts circularity, scans landing grids, and recommends EDM parameters. Leave-one-out "
            "validation and geometry-aware heuristics confirm that low current, long pulse-on, and high "
            "duty factor maximize supporting-ring circularity when the oversized tool overlaps pores, "
            "nodes, and struts simultaneously.",
            styles["abstract"],
        )
    )
    story.append(
        p(
            "<b>Keywords:</b> electrical discharge machining; metallic lattice; circularity; "
            "Gaussian process regression; gradient boosting; SEM validation; additive manufacturing post-processing",
            styles["keywords"],
        )
    )

    # --- 1. Introduction ---
    story.append(p("1. Introduction", styles["heading1"]))
    story.append(
        p(
            "Additive manufacturing enables complex metallic lattices with controlled porosity for "
            "orthopedic implants, heat exchangers, and structural lightweighting. After fabrication, "
            "secondary machining is often required to open or finish pores. Micro-EDM is attractive for "
            "hard alloys because material removal occurs by pulsed spark erosion without macroscopic "
            "cutting forces. However, when the electrode diameter exceeds the target pore, the process "
            "no longer machines a single cavity: the tool footprint spans nodes, open pores, and "
            "supporting struts at once. Preserving a continuous supporting ring while obtaining a "
            "circular machined boundary then becomes a coupled geometry–process problem.",
            styles["body"],
        )
    )
    story.append(
        p(
            "Prior EDM studies frequently optimize material removal rate, tool wear, or hole cylindricity "
            "using Taguchi designs or response-surface methods. Those scalar responses can mislead when "
            "the engineering goal is visual boundary integrity of thin supporting ligaments. In this "
            "project, SEM images of sixteen runs reveal a striking paradox: the trial with the best "
            "numerical hole-deviation score destroys the supporting ring, whereas a gentler, "
            "higher-energy-duration setting yields the only acceptable circular boundary. This paper "
            "documents that finding, formalizes Phase&nbsp;1 (position-agnostic) and Phase&nbsp;2 "
            "(position-aware) recommendations, and presents LatticeFlow — a machine-learning web "
            "application that predicts circularity over a 1500×1500&nbsp;µm working area.",
            styles["body"],
        )
    )
    story.append(
        p(
            "The contributions are: (i) geometry derivation of pore/node diameter from a 500&nbsp;µm unit "
            "cell and tool-to-pore ratio 3.82; (ii) SEM-based circularity labels replacing deviation-only "
            "ranking; (iii) Gaussian Process search and Gradient Boosting predictors blending EDM and "
            "lattice geometric features; and (iv) a deployed interactive analyzer with grid heatmaps, "
            "PASS/FAIL criteria, and an engineering report generator.",
            styles["body"],
        )
    )

    # --- 2. Problem formulation ---
    story.append(p("2. Problem Formulation and Lattice Geometry", styles["heading1"]))
    story.append(p("2.1 Physical configuration", styles["heading2"]))
    story.append(
        p(
            "The lattice comprises square unit cells of side <i>a</i> = 500&nbsp;µm. Nodes and open pores "
            "are modeled as equal-diameter circles of diameter <i>x</i>. Along the unit-cell diagonal,",
            styles["body_noindent"],
        )
    )
    story.append(
        p(
            "<i>a</i>√2 = 2·(<i>x</i>/2) + <i>x</i> = 3<i>x</i> &nbsp;⇒&nbsp; "
            "<i>x</i> = <i>a</i>√2 / 3 = 500√2 / 3 ≈ 235.6&nbsp;µm.",
            styles["body_noindent"],
        )
    )
    story.append(
        p(
            "The EDM tool tip diameter is 900&nbsp;µm, so the tool-to-pore ratio is 900/235.6 ≈ 3.82. "
            "Because the tool radius (450&nbsp;µm) is comparable to the unit cell, any landing position "
            "overlaps multiple cells. Phase&nbsp;2 therefore analyzes a 3×3 working area of "
            "1500×1500&nbsp;µm that fully contains the tool footprint.",
            styles["body"],
        )
    )

    story.append(p("2.2 Success criteria", styles["heading2"]))
    story.append(
        p(
            "Success requires a nearly circular open (white) region together with a continuous supporting "
            "(black) ring. Nodes (red in schematic diagrams) may be destroyed. Quantitative PASS gates "
            "used by the software are: circularity score ≥ 3.5/5, circularity ratio ≥ 0.70, supporting "
            "material intact, and geometry risk ≤ 0.55. Hole_Dev_Top/Bottom alone is explicitly "
            "<i>not</i> the primary metric.",
            styles["body"],
        )
    )

    geom_data = [
        [p(h, styles["table_header"]) for h in ["Parameter", "Value", "Source"]],
        [p("Unit cell side", styles["table_cell"]), p("500 µm", styles["table_cell"]), p("SEM scale", styles["table_cell"])],
        [p("Pore / node diameter", styles["table_cell"]), p("235.6 µm", styles["table_cell"]), p("3x = 500√2", styles["table_cell"])],
        [p("Tool tip diameter", styles["table_cell"]), p("900 µm", styles["table_cell"]), p("Lab specification", styles["table_cell"])],
        [p("Tool / pore ratio", styles["table_cell"]), p("3.82×", styles["table_cell"]), p("900 / 235.6", styles["table_cell"])],
        [p("Phase 2 working area", styles["table_cell"]), p("1500 × 1500 µm", styles["table_cell"]), p("3×3 unit cells", styles["table_cell"])],
    ]
    story.append(styled_table(geom_data, [2.0 * inch, 1.6 * inch, 2.0 * inch]))
    story.append(p("Table 1. Lattice and tool geometry constants used throughout the study.", styles["caption"]))

    story.extend(
        maybe_image(
            ROOT / "ACTUAL OUTPUT WE WANT.jpeg",
            5.2 * inch,
            "Figure 1. Target outcome: continuous supporting ring (black) and nearly circular open pore "
            "(white); nodes may be sacrificed.",
            styles,
        )
    )

    # --- 3. Experimental data ---
    story.append(p("3. Experimental Dataset", styles["heading1"]))
    story.append(
        p(
            "Sixteen real EDM trials form the ground-truth corpus. Controllable inputs are peak current "
            "<i>I</i> ∈ {4, 6, 8, 10}&nbsp;A, pulse-on time <i>T</i> ∈ {50, 75, 100, 150}&nbsp;µs, and duty "
            "factor <i>D</i> ∈ {56, 64, 72, 80}%. Recorded responses include tool wear rate, volume "
            "removal rate, and hole deviation at top and bottom. Independently, each run was labeled "
            "from SEM images on a 1–5 boundary-circularity scale and a binary supporting-boundary-intact "
            "flag. Only Run&nbsp;4 received circularity 5 with an intact supporting boundary.",
            styles["body"],
        )
    )

    run_header = [
        p(h, styles["table_header"])
        for h in ["Run", "I (A)", "T (µs)", "D (%)", "Dev top", "Dev bot", "Circ.", "Intact"]
    ]
    all_runs = [
        ("1", "4", "50", "56", "231.6", "213.9", "1", "No"),
        ("2", "4", "75", "64", "217.8", "199.1", "2", "No"),
        ("3", "4", "100", "72", "230.2", "212.1", "1", "No"),
        ("4*", "4", "150", "80", "270.6", "213.0", "5", "Yes"),
        ("5", "6", "50", "64", "205.3", "143.4", "2", "No"),
        ("6", "6", "75", "56", "225.4", "172.7", "2", "No"),
        ("7", "6", "100", "80", "280.5", "130.0", "1", "No"),
        ("8", "6", "150", "72", "219.7", "53.9", "2", "No"),
        ("9", "8", "50", "72", "240.2", "96.4", "2", "No"),
        ("10", "8", "75", "80", "260.5", "122.9", "1", "No"),
        ("11", "8", "100", "56", "240.3", "213.7", "1", "No"),
        ("12", "8", "150", "64", "213.9", "216.7", "2", "No"),
        ("13", "10", "50", "80", "238.6", "122.4", "1", "No"),
        ("14", "10", "75", "72", "251.6", "155.4", "2", "No"),
        ("15", "10", "100", "64", "227.1", "204.6", "2", "No"),
        ("16", "10", "150", "56", "231.9", "26.8", "1", "No"),
    ]
    run_rows = [run_header]
    for row in all_runs:
        run_rows.append([p(c, styles["table_cell"]) for c in row])
    story.append(
        styled_table(
            run_rows,
            [0.55 * inch, 0.55 * inch, 0.65 * inch, 0.6 * inch, 0.7 * inch, 0.7 * inch, 0.55 * inch, 0.6 * inch],
        )
    )
    story.append(
        p(
            "Table 2. Complete 16-run experimental matrix with SEM circularity labels "
            "(* = SEM reference success). Run 5 has lower top deviation than Run 4 but fails "
            "visual circularity of the supporting boundary.",
            styles["caption"],
        )
    )

    story.extend(
        maybe_image(
            ROOT / "ACTUAL IMAGE OF THE 16 DATASETS .png",
            6.2 * inch,
            "Figure 2. SEM montage of the sixteen experimental outcomes used for visual labeling.",
            styles,
        )
    )

    story.append(
        p(
            "An auxiliary set of 1,100 synthetic points was generated for exploratory Gradient Boosting "
            "augmentation. These points are <b>not</b> independent laboratory measurements; Phase&nbsp;1 "
            "recommendations reported as final answers use only the sixteen real runs with SEM labels.",
            styles["body"],
        )
    )

    # --- 4. Methodology ---
    story.append(p("4. Methodology", styles["heading1"]))
    story.append(p("4.1 Phase 1 — unknown tool position", styles["heading2"]))
    story.append(
        p(
            "When landing coordinates are unavailable, the objective is to identify robust EDM parameters "
            "that maximize expected supporting-boundary circularity anywhere on the lattice. Features "
            "are polynomial expansions (degree 2) of (<i>I</i>, <i>T</i>, <i>D</i>). A Ridge regressor "
            "under leave-one-out cross-validation (LOOCV) estimates circularity; a Gaussian Process "
            "Regressor with Matérn&nbsp;5/2 kernel plus WhiteKernel then searches thousands of candidates "
            "in a bounded input space, ranking by predicted mean plus a modest uncertainty bonus. "
            "Discharge energy <i>E</i> = <i>I</i>·<i>T</i>·(<i>D</i>/100) contextualizes intensity: "
            "Run&nbsp;4 yields <i>E</i> = 480 units versus 192 for Run&nbsp;5, yet energy is delivered "
            "gently through a small plasma channel and long pulse duration.",
            styles["body"],
        )
    )

    story.append(p("4.2 Phase 2 — known tool position", styles["heading2"]))
    story.append(
        p(
            "Given landing coordinates (<i>x</i>, <i>y</i>) in the 1500&nbsp;µm working area, a lattice "
            "geometry engine computes: minimum distance to strut and node, counts of nodes/pores inside "
            "the tool, strut intersection length, pore/node overlap fractions, and a geometry risk index. "
            "These features concatenate with EDM descriptors (<i>I</i>, <i>T</i>, <i>D</i>, energy, "
            "pulse-off, <i>I</i>×<i>D</i>, <i>T</i>/<i>D</i>, tool/pore ratio). Dual Gradient Boosting "
            "regressors predict circularity (1–5) and supporting integrity (0/1). Predictions blend with "
            "physics heuristics that reward low current (≤5&nbsp;A), long pulse-on (≥130&nbsp;µs), and "
            "high duty (≥75%), and penalize high geometry risk or currents ≥8&nbsp;A.",
            styles["body"],
        )
    )

    story.append(p("4.3 Feature construction", styles["heading2"]))
    story.append(
        p(
            "For each candidate landing point on a discrete grid (typical step 150&nbsp;µm), the geometry "
            "engine evaluates intersections between the circular tool footprint and the periodic lattice. "
            "Normalized coordinates (<i>x</i>/<i>W</i>, <i>y</i>/<i>W</i>) with <i>W</i> = 1500&nbsp;µm "
            "enter the model alongside absolute risk descriptors. Training expands the sixteen labeled "
            "runs across grid positions by modulating the SEM circularity label with a geometry penalty "
            "and an EDM bonus/penalty term, teaching the regressor that the same recipe degrades when "
            "strut overlap rises. Supporting-integrity targets are set to zero when current ≥ 8&nbsp;A or "
            "geometry risk is high, reflecting SEM evidence of blasted ligaments.",
            styles["body"],
        )
    )

    story.append(p("4.4 Software architecture", styles["heading2"]))
    story.append(
        p(
            "LatticeFlow is implemented as a Flask web service with modules for geometry "
            "(<font face='Courier'>lattice_geometry_engine.py</font>), prediction "
            "(<font face='Courier'>circularity_predictor.py</font>), synthetic visualization "
            "(<font face='Courier'>synthetic_view.py</font>), LLM chat assistance "
            "(<font face='Courier'>chat_assistant.py</font>), and automated engineering reports "
            "(<font face='Courier'>report_builder.py</font>). The inference path loads a persisted "
            "joblib ensemble, blends Gradient Boosting outputs with heuristics weighted by distance "
            "from the training manifold, and returns circularity, supporting integrity, geometry risk, "
            "and a PASS/FAIL decision. Users can analyze a single landing point, run a full-grid heatmap "
            "scan to locate the best (<i>x</i>, <i>y</i>), and export a multi-section engineering report. "
            "Deployment uses Gunicorn on Render.com with optional Anthropic/OpenAI keys for the assistant.",
            styles["body"],
        )
    )
    story.append(
        p(
            "End-to-end data flow: user inputs → parameter validation → geometry analysis at "
            "(<i>x</i>, <i>y</i>) → feature vector assembly → dual regressors + heuristic blend → "
            "scorecards and figures → optional LLM explanation. This separation keeps the physics/"
            "geometry layer testable independently of the UI and enables batch offline sweeps for "
            "parameter studies without launching the browser client.",
            styles["body"],
        )
    )

    story.extend(
        maybe_image(
            ROOT / "assets" / "Grid Scan For Circularity.png",
            5.4 * inch,
            "Figure 3. Application screenshot: grid scan circularity analysis over the lattice working area.",
            styles,
        )
    )

    # --- 5. Results ---
    story.append(p("5. Results and Discussion", styles["heading1"]))
    story.append(p("5.1 SEM-validated ranking", styles["heading2"]))
    story.append(
        p(
            "Ranking by SEM circularity places Run&nbsp;4 uniquely at the top (score 5, supporting intact). "
            "All other runs score 1–2 with destroyed or irregular boundaries. Notably, Run&nbsp;5 "
            "(6&nbsp;A, 50&nbsp;µs, 64%) achieves the smallest top-hole deviation among several mid-current "
            "trials yet fails visually — confirming that deviation minimization is an inadequate proxy "
            "for supporting-ring quality when the electrode overfills the pore.",
            styles["body"],
        )
    )
    story.append(
        p(
            "Mechanistically, Run&nbsp;4 combines a constrained plasma channel (low <i>I</i>), radially "
            "diffused erosion over a long pulse (high <i>T</i>), and steady duty (high <i>D</i>). Higher "
            "currents (≥8&nbsp;A) blast thin struts before a circular ring can form. Short pulses with "
            "moderate current produce asymmetric cratering. The recommended pattern is therefore "
            "<b>low current + long pulse-on + high duty</b>, with fine servo feed (1–5&nbsp;µm/step), "
            "stable gap voltage, continuous dielectric flushing, and a freshly dressed 900&nbsp;µm electrode.",
            styles["body"],
        )
    )

    story.append(p("5.2 Phase recommendations", styles["heading2"]))
    rec_header = [p(h, styles["table_header"]) for h in ["Case", "Zone", "I (A)", "T (µs)", "D (%)", "Trust"]]
    rec_rows = [
        rec_header,
        [p(c, styles["table_cell"]) for c in ["Phase 1 + SEM", "Any (unknown)", "4", "150", "80", "High"]],
        [p(c, styles["table_cell"]) for c in ["Phase 1 − SEM", "Any (unknown)", "6", "50", "64", "Low†"]],
        [p(c, styles["table_cell"]) for c in ["Phase 2 + SEM", "Pore center", "4", "150", "80", "High"]],
        [p(c, styles["table_cell"]) for c in ["Phase 2 + SEM", "Mid pore", "4", "148", "79", "High"]],
        [p(c, styles["table_cell"]) for c in ["Phase 2 + SEM", "Near strut", "3.5", "150", "78", "High"]],
        [p(c, styles["table_cell"]) for c in ["Phase 2 + SEM", "Near node (0,0)", "3.5", "145", "76", "High"]],
    ]
    story.append(
        styled_table(rec_rows, [1.25 * inch, 1.25 * inch, 0.7 * inch, 0.75 * inch, 0.7 * inch, 0.7 * inch])
    )
    story.append(
        p(
            "Table 3. Final parameter recommendations. †Deviation-only optimum — not recommended for "
            "supporting-boundary circularity.",
            styles["caption"],
        )
    )

    story.append(
        p(
            "Near-strut and near-node landings warrant slightly reduced current (3.5&nbsp;A) and marginally "
            "lower duty to protect ligaments already heavily overlapped by the 900&nbsp;µm tip. Gaussian "
            "Process candidate search clusters near 3.6–4.8&nbsp;A, ≈150&nbsp;µs, and ≈79–80% duty, with "
            "predicted circularity ≈4.6–4.9 on the 1–5 scale — consistent with the Run&nbsp;4 neighborhood.",
            styles["body"],
        )
    )

    story.append(p("5.3 Model validation notes", styles["heading2"]))
    story.append(
        p(
            "With only sixteen labeled experiments, LOOCV metrics must be interpreted cautiously. "
            "Polynomial Ridge LOOCV mean absolute error on circularity is on the order of one point on "
            "the 1–5 scale; R² for small-sample fits remains low. Consequently, models are decision-"
            "support tools anchored to the SEM reference, not substitutes for additional trials. "
            "Recommended follow-ups include 3.5&nbsp;A / 150&nbsp;µs / 80% and 4&nbsp;A / 140&nbsp;µs / 78% "
            "to probe robustness around Run&nbsp;4.",
            styles["body"],
        )
    )
    story.append(
        p(
            "Qualitatively, the deployed grid scanner reproduces the expected spatial structure: "
            "circularity peaks when the tool is centered on open pores with moderate strut clearance, "
            "and falls near dense node–strut junctions where geometry risk exceeds ~0.55. This spatial "
            "behavior cannot be recovered from EDM parameters alone and justifies the Phase&nbsp;2 "
            "feature set. Avoidance rules encoded in the heuristic layer — <i>I</i> ≥ 8&nbsp;A, "
            "<i>T</i> ≤ 75&nbsp;µs, or volume-removal indicators &gt; 0.9 — align with the SEM failures "
            "in Runs 7, 10, 11, 13, and 16.",
            styles["body"],
        )
    )

    story.append(p("5.4 Comparison of objective functions", styles["heading2"]))
    story.append(
        p(
            "Two competing objective functions were evaluated. Objective A minimizes a composite of "
            "Hole_Dev_Top and Hole_Dev_Bottom; Objective B maximizes SEM boundary circularity subject "
            "to supporting integrity. Objective A nominates Run&nbsp;5-like recipes and would mislead "
            "production toward destroyed rings. Objective B recovers Run&nbsp;4 and nearby gentle "
            "settings. The project therefore treats SEM-labeled circularity as the primary supervised "
            "target and retains deviation values only as secondary process monitors. This objective "
            "choice is the single most consequential methodological decision in the study.",
            styles["body"],
        )
    )

    # --- 6. Discussion implications ---
    story.append(p("6. Engineering Implications", styles["heading1"]))
    story.append(
        p(
            "For practitioners finishing AM lattices with oversized EDM electrodes, three lessons emerge. "
            "First, define success from the supporting topology that must survive, not from hole-size "
            "deviation alone. Second, when tool/pore ≫ 1, gentle high-duty long-pulse recipes outperform "
            "aggressive short pulses even if the latter look better on scalar metrology. Third, "
            "position-aware models matter: the same EDM recipe can PASS at a pore center and FAIL near "
            "a strut because geometry risk and strut intersection length change rapidly within one "
            "unit cell.",
            styles["body"],
        )
    )
    story.append(
        p(
            "The interactive heatmap converts these insights into shop-floor guidance: engineers enter "
            "candidate parameters, visualize spatial circularity, and receive zone-specific "
            "recommendations before committing scarce SEM time. The optional LLM assistant explains "
            "PASS/FAIL outcomes in engineering language, lowering the barrier between data science "
            "outputs and process decisions.",
            styles["body"],
        )
    )

    story.extend(
        maybe_image(
            ROOT / "MEASURMEBN.jpeg",
            4.8 * inch,
            "Figure 4. Geometric construction used to derive pore diameter 235.6 µm from the 500 µm unit cell.",
            styles,
        )
    )

    # --- 7. Limitations ---
    story.append(p("7. Limitations and Future Work", styles["heading1"]))
    story.append(
        p(
            "The labeled set is small and unbalanced (one clear success). Material alloy, dielectric, "
            "and electrode wear dynamics are not modeled explicitly. Synthetic augmentation must not be "
            "confused with new experiments. Future work should (i) expand the SEM-labeled design of "
            "experiments around the Run&nbsp;4 neighborhood; (ii) incorporate image-based circularity "
            "from automated contour analysis; (iii) couple thermal-plasma simulation with the geometry "
            "engine; and (iv) close the loop by writing recommended (<i>I</i>, <i>T</i>, <i>D</i>, "
            "<i>x</i>, <i>y</i>) directly to machine controllers.",
            styles["body"],
        )
    )

    # --- 8. Conclusion ---
    story.append(p("8. Conclusion", styles["heading1"]))
    story.append(
        p(
            "This research paper consolidates laboratory evidence, geometric analysis, and machine-"
            "learning tooling for EDM finishing of metallic lattices when the electrode is 3.82× larger "
            "than the pore. SEM validation establishes Run&nbsp;4 (4&nbsp;A, 150&nbsp;µs, 80%) as the "
            "sole supporting-ring success among sixteen trials and overturns a deviation-minimizing "
            "alternative. Phase&nbsp;1 and Phase&nbsp;2 recommendations, geometry-aware Gradient Boosting, "
            "and the LatticeFlow web application provide a practical pathway from sparse experiments to "
            "position-specific process guidance. Additional trials near the identified gentle-parameter "
            "island remain the highest-value next step for industrial adoption.",
            styles["body"],
        )
    )

    # --- Acknowledgments / refs ---
    story.append(p("Acknowledgments", styles["heading1"]))
    story.append(
        p(
            "The authors acknowledge the laboratory team who conducted the sixteen EDM trials and "
            "provided SEM imagery, and the open-source ecosystem (scikit-learn, Flask, ReportLab) "
            "supporting the LatticeFlow implementation.",
            styles["body"],
        )
    )

    story.append(p("References", styles["heading1"]))
    refs = [
        "[1] Ho, K. H., &amp; Newman, S. T. (2003). State of the art electrical discharge machining (EDM). "
        "<i>International Journal of Machine Tools and Manufacture</i>, 43(13), 1287–1300.",
        "[2] Kunieda, M., Lauwers, B., Rajurkar, K. P., &amp; Schumacher, B. M. (2005). Advancing EDM through "
        "fundamental insight into the process. <i>CIRP Annals</i>, 54(2), 64–87.",
        "[3] Gibson, I., Rosen, D., &amp; Stucker, B. (2021). <i>Additive Manufacturing Technologies</i> "
        "(3rd ed.). Springer.",
        "[4] Ashby, M. F., et al. (2000). Metal foams: A design guide. Butterworth-Heinemann. "
        "(Lattice / cellular metal design context.)",
        "[5] Rasmussen, C. E., &amp; Williams, C. K. I. (2006). <i>Gaussian Processes for Machine Learning</i>. "
        "MIT Press.",
        "[6] Friedman, J. H. (2001). Greedy function approximation: A gradient boosting machine. "
        "<i>Annals of Statistics</i>, 29(5), 1189–1232.",
        "[7] Lattice Circularity Analyzer Project (2026). Internal laboratory dataset: 16 EDM runs with "
        "SEM circularity labels; geometry constants and recommended trials "
        "(<font face='Courier'>data/original_16_runs.csv</font>, "
        "<font face='Courier'>data/run_visual_labels.csv</font>).",
        "[8] LatticeFlow software modules (2026). "
        "<font face='Courier'>phase1_model_actual.py</font>, "
        "<font face='Courier'>circularity_predictor.py</font>, "
        "<font face='Courier'>lattice_geometry_engine.py</font>, "
        "<font face='Courier'>web_server.py</font>. GitHub: Lattice-Circularity-Analyzer.",
        "[9] ISO 12181 / related form-measurement practice (context). Circularity evaluation of "
        "engineered features (adapted here to SEM boundary judgment on micro-lattices).",
        "[10] Project ideation notes (15 June 2026). Grid subdivision logic for Phase 2 working area "
        "and ML circularity mapping over unit-cell intersections.",
    ]
    for r in refs:
        story.append(p(r, styles["ref"]))

    story.append(Spacer(1, 16))
    story.append(
        p(
            "<i>Appendix note.</i> Full 16-run numerical tables, recommended trial matrices, and "
            "JSON model outputs are archived in the project repository under "
            "<font face='Courier'>data/</font> and <font face='Courier'>outputs/</font>. "
            "Live deployment reference: Lattice Circularity Analyzer web application.",
            styles["body_noindent"],
        )
    )

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)

    # Page count check
    from pypdf import PdfReader

    n_pages = len(PdfReader(str(OUTPUT)).pages)
    print(f"Saved: {OUTPUT} ({n_pages} pages)")
    return n_pages


if __name__ == "__main__":
    build()
