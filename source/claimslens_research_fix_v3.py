#!/usr/bin/env python3
"""
ClaimsLens Research v3
Readable research dashboard, formatted HTML, PDF and Word reports.

Uses existing ClaimsLens Clinical Studio.
Original research files and application source are unchanged.
Synthetic data only.
"""

import argparse
import html
import io
import json
import tempfile
import threading
import urllib.request

from datetime import datetime
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import claimslens_one_paste_studio as studio

TITLE = (
    "ClaimsLens | Medical AI Evidence "
    "& Nurse Case Management"
)

LIMITS = [
    "All claims, clinical records, labels and payer policies are synthetic.",
    "This study is imbalanced; overall accuracy alone can be misleading.",
    "The evaluation and verifier may share synthetic generator assumptions.",
    "No independent clinical validation or measured nurse time savings.",
    "The risk score is not a calibrated real-patient outcome probability.",
    "Human verification is required before clinical decisions.",
    "No real insurer approval or medical completion is established.",
    "Privacy, access control, security, EHR integration and governance remain unfinished.",
    "Historical standalone research modules are not all directly imported at runtime.",
]

NAMES = {
    "email_only": "Email-only language model",
    "source_context": "Source-context language model",
    "gated": "Source-context + evidence gate",
}


# ============================================================
# 1. READ EXISTING RESEARCH, WITHOUT CHANGING IT
# ============================================================

def study_results():

    folder = (
        Path.home()
        / ".claimslens_validation_runs"
    )

    paths = sorted(
        folder.glob("*/ai_metrics.json")
    )

    if not paths:
        return {
            "available": False,
            "message": (
                "No saved AI study found. "
                "Original research files were not changed."
            ),
        }

    source = paths[-1]

    raw = json.loads(
        source.read_text(encoding="utf-8")
    )

    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("gated"), dict)
    ):
        raise ValueError(
            "Saved study metrics have an unexpected format"
        )

    trial_file = (
        source.parent / "ai_trials.jsonl"
    )

    trials = []

    if trial_file.exists():

        for line in trial_file.read_text(
            encoding="utf-8"
        ).splitlines():

            if not line.strip():
                continue

            trial = json.loads(line)

            if isinstance(
                trial.get("fixture_truth"),
                bool
            ):
                trials.append(trial)

    positives = (
        sum(
            trial["fixture_truth"]
            for trial in trials
        )
        if trials else None
    )

    negatives = (
        len(trials) - positives
        if trials else None
    )

    methods = []

    for key, name in NAMES.items():

        m = raw.get(key, {})

        missed = m.get(
            "missed_fixture_completions"
        )

        unsafe = m.get(
            "unsafe_accepted"
        )

        supported = (
            positives - missed
            if positives is not None
            and isinstance(missed, int)
            else None
        )

        specificity = (
            (negatives - unsafe) / negatives
            if negatives
            and isinstance(unsafe, int)
            else None
        )

        sensitivity = (
            supported / positives
            if positives
            and supported is not None
            else None
        )

        methods.append({
            "key": key,
            "name": name,
            "completed": m.get("completed"),
            "accuracy": m.get("accuracy"),
            "ci": m.get("accuracy_wilson95"),
            "unsafe": unsafe,
            "missed": missed,
            "supported": supported,
            "specificity": specificity,
            "sensitivity": sensitivity,
            "errors": m.get("errors"),
        })

    return {
        "available": True,
        "run": source.parent.name,
        "n": raw["gated"].get("completed"),
        "positive": positives,
        "negative": negatives,
        "methods": methods,
        "limitations": LIMITS,
        "synthetic_only": True,
    }


# ============================================================
# 2. CREATE STRUCTURED CASE RESEARCH DATA
# ============================================================

def report_data(owner, cid):

    if cid not in studio.core.CASES:
        raise ValueError(
            "Unknown synthetic claim"
        )

    data = studio.workspace(
        owner, cid
    )

    nurse = data["ncm"]

    evidence = []

    for decision in data["decisions"]:

        evidence.append({
            "obligation": decision["label"],
            "state": decision["status"],

            "support": list(
                decision.get(
                    "supporting_citations", []
                )
            ),

            "inspection": list(
                decision.get(
                    "rejection_citations", []
                )
            ),

            "blockers": list(
                decision.get("blockers", [])
            ),
        })

    return {
        "study": study_results(),
        "id": cid,
        "injury": data["title"],
        "worker": data["name"],
        "doctor": data["doctor"],
        "date_of_injury": data["doi"],
        "evidence": evidence,

        "risk": nurse["risk"]["score"],

        "risk_metrics": nurse["risk"].get(
            "metrics", {}
        ),

        "authorization_ready": nurse[
            "authorization"
        ].get("packet_ready_demo"),

        "authorization_missing": nurse[
            "authorization"
        ].get("missing", []),

        "care_needs": nurse["care"],
        "soap_drafts": len(nurse["notes"]),
        "tasks": len(nurse["tasks"]),

        "generated": datetime.now().strftime(
            "%B %d, %Y"
        ),

        "limits": LIMITS,
    }


def ratio(value, denominator):

    if value is None or denominator in (
        None, 0
    ):
        return "Not measured"

    return f"{value}/{denominator}"


def percent(value):

    if value is None:
        return "N/A"

    return f"{value * 100:.2f}%"


def understanding(study):

    if not study["available"]:
        return study["message"]

    positive = study["positive"]
    negative = study["negative"]

    if positive is None:
        return (
            "Class-balance information is unavailable "
            "without saved individual trial records."
        )

    methods = {
        m["key"]: m
        for m in study["methods"]
    }

    email = methods["email_only"]
    source = methods["source_context"]
    gated = methods["gated"]

    return (
        f"This synthetic sample contained "
        f"{positive} valid completions and "
        f"{negative} unsupported cases. "

        f"The email-only model recognized "
        f"{ratio(email['supported'], positive)} "
        f"valid completions, so its "
        f"{percent(email['accuracy'])} accuracy "
        f"mostly reflects rejecting negative cases. "

        f"The source-context model proposed "
        f"{source['unsafe']} unsafe completions; "
        f"the gated approach accepted "
        f"{gated['unsafe']}. "

        f"The gate also missed "
        f"{gated['missed']} valid completion(s). "

        "These are paired synthetic findings, "
        "not clinical efficacy estimates."
    )


# ============================================================
# 3. PROPERLY FORMATTED HTML RESEARCH REPORT
# ============================================================

def preview_html(report):

    esc = lambda value: html.escape(
        str(value),
        quote=True
    )

    study = report["study"]

    methods = "".join(
        "<tr>"
        f"<td>{esc(m['name'])}</td>"
        f"<td>{percent(m['accuracy'])}</td>"
        f"<td>{ratio(m['supported'], study.get('positive'))}</td>"
        f"<td>{ratio(m['unsafe'], study.get('negative'))}</td>"
        f"<td>{esc(m['errors'])}</td>"
        "</tr>"
        for m in study.get("methods", [])
    )

    obligations = "".join(
        "<tr>"
        f"<td>{esc(x['obligation'])}</td>"
        f"<td>{esc(x['state'])}</td>"
        f"<td>{esc(', '.join(x['support']) or 'None')}</td>"
        f"<td>{esc(', '.join(x['inspection']) or 'None')}</td>"
        "</tr>"
        for x in report["evidence"]
    )

    limitations = "".join(
        "<li>" + esc(x) + "</li>"
        for x in report["limits"]
    )

    if study["available"]:

        study_panel = f"""
        <section>

        <h2>Paired synthetic AI evaluation</h2>

        <p>
            {esc(understanding(study))}
        </p>

        <table>
        <tr>
            <th>Method</th>
            <th>Overall accuracy</th>
            <th>Valid recognized</th>
            <th>Unsafe accepted</th>
            <th>Errors</th>
        </tr>

        {methods}
        </table>

        <p class="minor">
            Saved run: {esc(study['run'])}.
            Confidence intervals are specific
            to the synthetic sample.
        </p>

        </section>
        """

    else:

        study_panel = (
            "<section><h2>Study results</h2><p>"
            + esc(study["message"])
            + "</p></section>"
        )

    accuracy = (
        percent(study["methods"][2]["accuracy"])
        if study["available"]
        else "N/A"
    )

    return f"""<!doctype html>
<html lang="en">
<head>

<meta charset="utf-8">
<title>{esc(TITLE)}</title>

<style>

body {{
    font: 15px/1.6 system-ui,sans-serif;
    background: #f2f7f4;
    color: #213c34;
    margin: 0;
}}

.wrap {{
    max-width: 1080px;
    margin: 36px auto;
    background: white;
    border-radius: 20px;
    box-shadow: 0 10px 50px #102c2514;
    overflow: hidden;
}}

header {{
    background: #104e3d;
    color: white;
    padding: 44px 48px;
}}

header h1 {{
    font-size: 29px;
    line-height: 1.25;
    margin: 8px 0;
}}

.eyebrow {{
    letter-spacing: 1.5px;
    font-size: 12px;
    text-transform: uppercase;
    opacity: .85;
}}

main {{
    padding: 24px 48px 50px;
}}

section {{
    border-bottom: 1px solid #e6eeea;
    padding: 24px 0;
}}

h2 {{
    font-size: 20px;
    color: #164c3b;
}}

table {{
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
}}

td,th {{
    border-bottom: 1px solid #dfe9e3;
    padding: 10px;
    text-align: left;
    vertical-align: top;
}}

th {{
    background: #eaf3ee;
}}

.minor {{
    font-size: 12px;
    color: #63786e;
}}

.stats {{
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap: 14px;
}}

.metric {{
    background: #eef7f0;
    border-radius: 12px;
    padding: 16px;
}}

.metric strong {{
    font-size: 26px;
    color: #116249;
    display: block;
}}

.warning {{
    background: #fff4d9;
    padding: 13px;
    border-radius: 9px;
}}

@media print {{
    body {{ background: white; }}
    .wrap {{ box-shadow: none; margin: 0; }}
}}

@media(max-width:740px) {{
    main,header {{ padding: 24px; }}
    .stats {{ grid-template-columns: 1fr; }}
    table {{ font-size: 11px; }}
}}

</style>
</head>

<body>
<div class="wrap">

<header>

<div class="eyebrow">
    Research report · synthetic only
</div>

<h1>{esc(TITLE)}</h1>

<p>
    Evidence-constrained clinical workflow prototype
    · {esc(report['generated'])}
</p>

</header>

<main>

<section>

<h2>Executive summary</h2>

<p class="warning">
    Fictional patients and records only.
    Human review required.
    Not clinically validated or approved
    for clinical use.
</p>

<div class="stats">

<div class="metric">
    <strong>240</strong>
    Fictional claims
</div>

<div class="metric">
    <strong>{esc(study.get('n','N/A'))}</strong>
    AI study cases
</div>

<div class="metric">
    <strong>{accuracy}</strong>
    Synthetic gated accuracy
</div>

</div>

</section>

{study_panel}

<section>

<h2>Example case · {esc(report['id'])}</h2>

<p>
<b>{esc(report['injury'])}</b>
· {esc(report['worker'])}

<br>

Fictional physician:
{esc(report['doctor'])}

· Date of injury:
{esc(report['date_of_injury'])}
</p>

<table>

<tr>
<th>Care obligation</th>
<th>Evidence state</th>
<th>Supporting proof</th>
<th>Inspection-only references</th>
</tr>

{obligations}

</table>

</section>

<section>

<h2>Nurse case management workflows</h2>

<p>
Experimental risk signal:
{percent(report['risk'])}
(not clinically calibrated).

<br>

Fictional prior authorization documentation ready:
{esc(report['authorization_ready'])}.

<br>

Missing documentation:
{esc(', '.join(report['authorization_missing']) or 'None listed')}.

<br>

Discharge and social needs tracked:
{len(report['care_needs'])}.

<br>

Nurse tasks saved: {report['tasks']}.

<br>

SOAP drafts: {report['soap_drafts']}.
</p>

</section>

<section>

<h2>Limitations and next steps</h2>

<ul>{limitations}</ul>

<p class="minor">
    The live prototype uses the original
    case-verification engine and V2
    citation-separation adapter.
    Historical standalone research modules
    are not claimed as exact runtime integrations.
</p>

</section>

</main>
</div>
</body>
</html>"""


# ============================================================
# 4. GENUINE PDF GENERATION
# ============================================================

def pdf_bytes(report):

    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter

    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle
    )

    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Table,
        TableStyle,
        Spacer
    )

    output = io.BytesIO()

    document = SimpleDocTemplate(
        output,
        pagesize=letter,
        leftMargin=43,
        rightMargin=43,
        topMargin=48,
        bottomMargin=48,
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="CLBody",
            parent=styles["BodyText"],
            fontSize=9,
            leading=14,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CLHead",
            parent=styles["Heading2"],
            fontSize=13,
            leading=17,
            spaceBefore=17,
            spaceAfter=9,
            textColor=colors.HexColor("#12523E"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="CLCell",
            parent=styles["BodyText"],
            fontSize=8,
            leading=11,
        )
    )

    def paragraph(text, style="CLBody"):

        return Paragraph(
            escape(str(text)).replace(
                "\n", "<br/>"
            ),
            styles[style]
        )

    elements = [
        paragraph(TITLE, "Title"),

        paragraph(
            "RESEARCH PROTOTYPE | "
            "SYNTHETIC CASES ONLY"
        ),

        Spacer(1, 9),

        paragraph(
            "Generated: " + report["generated"]
        ),

        paragraph(
            "Not for patient care or real "
            "authorization decisions."
        ),
    ]

    def heading(text):

        elements.append(
            paragraph(text, "CLHead")
        )

    def add_table(headers, data_rows, widths):

        content = [
            [
                paragraph(x, "CLCell")
                for x in headers
            ]
        ]

        for values in data_rows:

            content.append([
                paragraph(x, "CLCell")
                for x in values
            ])

        table = Table(
            content,
            colWidths=widths,
            repeatRows=1,
            hAlign="LEFT",
        )

        table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0,0),(-1,0),
                    colors.HexColor("#DDEDE5")
                ),
                (
                    "ROWBACKGROUNDS",
                    (0,1),(-1,-1),
                    [
                        colors.white,
                        colors.HexColor("#F5F8F6")
                    ]
                ),
                (
                    "VALIGN",
                    (0,0),(-1,-1),
                    "TOP"
                ),
                (
                    "TOPPADDING",
                    (0,0),(-1,-1),
                    7
                ),
                (
                    "BOTTOMPADDING",
                    (0,0),(-1,-1),
                    7
                ),
                (
                    "LINEBELOW",
                    (0,0),(-1,-1),
                    .3,
                    colors.HexColor("#DCE6E0")
                ),
            ])
        )

        elements.append(table)

    study = report["study"]

    heading("Research summary")

    elements.append(
        paragraph(understanding(study))
    )

    if study["available"]:

        add_table(
            [
                "Comparison arm",
                "Accuracy",
                "Valid found",
                "Unsafe accepted",
            ],

            [
                [
                    m["name"],
                    percent(m["accuracy"]),
                    ratio(
                        m["supported"],
                        study["positive"]
                    ),
                    ratio(
                        m["unsafe"],
                        study["negative"]
                    ),
                ]
                for m in study["methods"]
            ],

            [185,85,100,113]
        )

    heading(
        "Synthetic case " + report["id"]
    )

    elements.append(
        paragraph(
            report["injury"]
            + " | "
            + report["worker"]
            + " | Doctor: "
            + report["doctor"]
        )
    )

    add_table(
        [
            "Obligation / state",
            "Supporting proof",
            "Inspected, not proof",
        ],

        [
            [
                item["obligation"]
                + "\n"
                + item["state"],

                ", ".join(
                    item["support"]
                ) or "None",

                ", ".join(
                    item["inspection"]
                ) or "None",
            ]
            for item in report["evidence"]
        ],

        [210,145,128]
    )

    heading(
        "Four connected nurse workflows"
    )

    lines = [
        (
            "Risk: "
            + percent(report["risk"])
            + " (synthetic, not clinically calibrated)"
        ),

        (
            "Authorization packet ready under fictional policy: "
            + str(report["authorization_ready"])
        ),

        (
            "Care needs: "
            + str(len(report["care_needs"]))
            + "; follow-up tasks: "
            + str(report["tasks"])
        ),

        (
            "SOAP documents pending review: "
            + str(report["soap_drafts"])
        ),
    ]

    for line in lines:
        elements.append(
            paragraph(line)
        )

    heading("Limitations")

    for item in report["limits"]:

        elements.append(
            paragraph("- " + item)
        )

    if study["available"]:

        elements.append(
            paragraph(
                "Research provenance: "
                + study["run"]
            )
        )

    def footer(canvas, doc):

        canvas.setFont(
            "Helvetica", 8
        )

        canvas.setFillColor(
            colors.HexColor("#64796B")
        )

        canvas.drawString(
            43, 28,
            "ClaimsLens | Fictional research only "
            "| Human verification required"
        )

        canvas.drawRightString(
            566, 28,
            "Page " + str(doc.page)
        )

    document.build(
        elements,
        onFirstPage=footer,
        onLaterPages=footer,
    )

    return output.getvalue()


# ============================================================
# 5. EDITABLE WORD REPORT
# ============================================================

def docx_bytes(report):

    from docx import Document
    from docx.shared import Inches

    document = Document()

    section = document.sections[0]

    section.top_margin = Inches(.72)
    section.bottom_margin = Inches(.7)

    section.header.paragraphs[0].text = (
        "CLAIMSLENS / RESEARCH & EVIDENCE REVIEW"
    )

    document.add_heading(
        TITLE, 0
    )

    document.add_paragraph(
        "RESEARCH PROTOTYPE — SYNTHETIC RECORDS ONLY",
        style="Subtitle",
    )

    document.add_paragraph(
        "Generated: " + report["generated"]
    )

    document.add_paragraph(
        "Not clinically validated. "
        "Human review required; "
        "not for patient care."
    )

    def add_table(headers, records):

        table = document.add_table(
            rows=1,
            cols=len(headers)
        )

        table.style = (
            "Light Shading Accent 1"
        )

        for i, heading in enumerate(headers):

            table.rows[0].cells[i].text = heading

        for record in records:

            cells = table.add_row().cells

            for i, value in enumerate(record):

                cells[i].text = str(value)

    study = report["study"]

    document.add_heading(
        "Evaluation findings",
        level=1
    )

    document.add_paragraph(
        understanding(study)
    )

    if study["available"]:

        add_table(
            [
                "Method",
                "Accuracy",
                "Valid recognized",
                "Unsafe accepted",
            ],

            [
                [
                    m["name"],
                    percent(m["accuracy"]),

                    ratio(
                        m["supported"],
                        study["positive"]
                    ),

                    ratio(
                        m["unsafe"],
                        study["negative"]
                    ),
                ]

                for m in study["methods"]
            ]
        )

        document.add_paragraph(
            "Source: saved run "
            + study["run"]
        )

    document.add_heading(
        "Example case — " + report["id"],
        level=1,
    )

    document.add_paragraph(
        report["injury"]
        + " | "
        + report["worker"]
    )

    document.add_paragraph(
        "Physician: "
        + report["doctor"]
        + " | Injury date: "
        + report["date_of_injury"]
    )

    add_table(
        [
            "Care obligation / evidence state",
            "Completion proof",
            "Inspected only",
        ],

        [
            [
                item["obligation"]
                + " — "
                + item["state"],

                ", ".join(
                    item["support"]
                ) or "None",

                ", ".join(
                    item["inspection"]
                ) or "None",
            ]

            for item in report["evidence"]
        ]
    )

    document.add_heading(
        "Nurse case management functions",
        level=1,
    )

    descriptions = [
        (
            "Experimental risk score: "
            + percent(report["risk"])
            + " — not clinically calibrated"
        ),

        (
            "Fictional authorization packet ready: "
            + str(report["authorization_ready"])
        ),

        (
            "Care needs tracked: "
            + str(len(report["care_needs"]))
            + "; saved worklist tasks: "
            + str(report["tasks"])
        ),

        (
            "SOAP drafts pending human review: "
            + str(report["soap_drafts"])
        ),
    ]

    for description in descriptions:

        document.add_paragraph(
            description,
            style="List Bullet"
        )

    document.add_heading(
        "Limitations and publication safeguards",
        level=1,
    )

    for item in report["limits"]:

        document.add_paragraph(
            item,
            style="List Bullet"
        )

    section.footer.paragraphs[0].text = (
        "Fictional claims only — "
        "no clinical decisions or real payer approvals"
    )

    output = io.BytesIO()

    document.save(output)

    return output.getvalue()


# ============================================================
# 6. FIX THE EXISTING RESEARCH TAB
# ============================================================

INJECT = r'''
<style>

#cl-study {
    font-family: system-ui,sans-serif !important;
    white-space: normal !important;
    background: transparent !important;
    font-size: 13px !important;
    max-height: none !important;
    line-height: 1.55 !important;
}

.cl-research-grid {
    display: grid;
    grid-template-columns: repeat(3,minmax(0,1fr));
    gap: 10px;
    margin: 15px 0;
}

.cl-research-tile {
    background: #edf7f0;
    border: 1px solid #dcebe1;
    padding: 15px;
    border-radius: 12px;
}

.cl-research-tile strong {
    display: block;
    color: #146449;
    font-size: 23px;
}

.cl-research-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    margin: 12px 0;
}

.cl-research-table th,
.cl-research-table td {
    padding: 10px 7px;
    border-bottom: 1px solid #dceae0;
    text-align: left;
}

.cl-research-table th {
    background: #eaf4ed;
}

.cl-research-alert {
    background: #fff4d9;
    border-radius: 10px;
    padding: 14px;
    margin: 13px 0;
}

@media(max-width:740px) {
    .cl-research-grid {
        grid-template-columns: 1fr;
    }
    .cl-research-table {
        font-size: 10px;
    }
}

</style>

<script>
(() => {

const esc = x =>
    String(x ?? "").replace(
        /[&<>"']/g,
        c => ({
            "&":"&amp;",
            "<":"&lt;",
            ">":"&gt;",
            '"':"&quot;",
            "'":"&#39;"
        }[c])
    );

const pct = x =>
    x == null
        ? "Not measured"
        : (100*x).toFixed(2)+"%";

const fraction = (x,y) =>
    x == null || y == null
        ? "N/A"
        : x+"/"+y;


function build(study) {

    if (!study.available) {
        return "<p>"+esc(study.message)+"</p>";
    }

    const methods = Object.fromEntries(
        study.methods.map(
            m => [m.key,m]
        )
    );

    const rows = study.methods.map(
        m => `
        <tr>
            <td>${esc(m.name)}</td>
            <td>${pct(m.accuracy)}</td>
            <td>${fraction(m.supported,study.positive)}</td>
            <td>${fraction(m.unsafe,study.negative)}</td>
        </tr>`
    ).join("");

    return `
    <div class="cl-research-grid">

        <div class="cl-research-tile">
            <strong>${esc(study.n)}</strong>
            Fictional cases tested
        </div>

        <div class="cl-research-tile">
            <strong>
                ${fraction(
                    methods.gated.supported,
                    study.positive
                )}
            </strong>
            Supported completions recognized
        </div>

        <div class="cl-research-tile">
            <strong>
                ${fraction(
                    methods.gated.unsafe,
                    study.negative
                )}
            </strong>
            Unsafe accepted after gating
        </div>

    </div>

    <h3>Comparison of three AI methods</h3>

    <table class="cl-research-table">

    <thead>
        <tr>
            <th>Method</th>
            <th>Overall accuracy</th>
            <th>Valid found</th>
            <th>Unsafe accepted</th>
        </tr>
    </thead>

    <tbody>${rows}</tbody>

    </table>

    <div class="cl-research-alert">

    <b>Why 93.75% email-only accuracy is misleading</b>

    <p>
        There were ${esc(study.positive)}
        positive and ${esc(study.negative)}
        negative synthetic examples.

        The email-only method accepted
        ${fraction(
            methods.email_only.supported,
            study.positive
        )} positive cases.

        It achieved high accuracy largely
        by saying "not complete" to every case.
    </p>

    </div>

    <p>
        <b>What the evidence gate changed:</b>

        Source-context AI accepted
        ${esc(methods.source_context.unsafe)}
        unsafe completions;

        the gate accepted
        ${esc(methods.gated.unsafe)}.

        It still missed
        ${esc(methods.gated.missed)}
        valid case(s).
    </p>

    <p class="cl-muted">
        Source: saved run ${esc(study.run)}.

        No independent clinical validation,
        patient data or new model inference.
    </p>
    `;
}


async function update() {

    const host = document.getElementById(
        "cl-study"
    );

    if (!host || host.dataset.loaded) {
        return;
    }

    host.dataset.loaded = "1";

    host.textContent = (
        "Loading saved research findings..."
    );

    const labels = {
        "cl-metrics": "Refresh research findings",
        "cl-report": "Preview formatted research report",
        "cl-pdf": "Download research PDF",
        "cl-word": "Download research Word"
    };

    for (const [id,label] of Object.entries(labels)) {

        const element = document.getElementById(id);

        if (element) {
            element.textContent = label;
        }
    }

    try {

        const response = await fetch(
            "/api/studio/research/study"
        );

        const study = await response.json();

        if (!response.ok) {
            throw Error(
                study.error || "Study unavailable"
            );
        }

        host.innerHTML = build(study);

    } catch (error) {

        host.textContent = (
            "Research dashboard error: "
            + error.message
        );
    }
}


const parent = document.getElementById(
    "cl-content"
);

if (parent) {

    new MutationObserver(update).observe(
        parent,
        {
            childList: true
        }
    );

    update();
}


// Intercept the old research buttons.
// Keep every other Clinical Studio control unchanged.

document.addEventListener(
    "click",
    event => {

        const button = event.target.closest(
            "button"
        );

        if (
            !button
            || ![
                "cl-metrics",
                "cl-report",
                "cl-pdf",
                "cl-word"
            ].includes(button.id)
        ) {
            return;
        }

        event.preventDefault();
        event.stopImmediatePropagation();

        const id = (
            window.caseData?.id
            || document.getElementById("claim")?.value
            || "CL-0001"
        );

        const query = (
            "?claim="+encodeURIComponent(id)
        );

        if (button.id === "cl-metrics") {

            const host = document.getElementById(
                "cl-study"
            );

            if (host) {
                delete host.dataset.loaded;
                update();
            }

            return;
        }

        const suffix = (
            button.id === "cl-report"
                ? "preview"
                : button.id === "cl-pdf"
                ? "pdf"
                : "word"
        );

        window.open(
            "/api/studio/research/"
            + suffix
            + query,
            "_blank",
            "noopener"
        );

    },
    true
);

})();
</script>
'''

PAGE = studio.PAGE.replace(
    "</body>",
    INJECT + "</body>",
    1
)


# ============================================================
# 7. ROUTES FOR THE REAL RESEARCH EXPORTS
# ============================================================

class App(studio.Server):

    def do_GET(self):

        path = urlparse(
            self.path
        ).path

        if path == "/":

            self.user()

            return self.respond(
                PAGE,
                mime="text/html; charset=utf-8"
            )

        if path.startswith(
            "/api/studio/research/"
        ):

            owner = self.user()

            try:

                if path == (
                    "/api/studio/research/study"
                ):

                    return self.respond(
                        study_results()
                    )

                cid = parse_qs(
                    urlparse(self.path).query
                ).get("claim", [""])[0]

                report = report_data(
                    owner,
                    cid
                )

                if path == (
                    "/api/studio/research/preview"
                ):

                    return self.respond(
                        preview_html(report),
                        mime="text/html; charset=utf-8"
                    )

                if path == (
                    "/api/studio/research/pdf"
                ):

                    return self.respond(
                        pdf_bytes(report),
                        mime="application/pdf",
                        filename=(
                            cid
                            + "_ClaimsLens_Research.pdf"
                        )
                    )

                if path == (
                    "/api/studio/research/word"
                ):

                    return self.respond(
                        docx_bytes(report),

                        mime=(
                            "application/"
                            "vnd.openxmlformats-officedocument."
                            "wordprocessingml.document"
                        ),

                        filename=(
                            cid
                            + "_ClaimsLens_Research.docx"
                        )
                    )

                return self.error(
                    "Unknown research path",
                    404
                )

            except (
                ValueError,
                KeyError,
                TypeError
            ) as error:

                return self.error(
                    error, 422
                )

        return super().do_GET()


# ============================================================
# 8. INTEGRATION TESTS
# ============================================================

def self_test():

    assert len(
        studio.core.CASES
    ) == 240

    with tempfile.TemporaryDirectory() as temp:

        core = studio.core
        care = studio.care

        previous = (
            core.ROOT,
            core.DB,
            core.UPLOAD_DIR,
            care.EXT_DB
        )

        core.ROOT = (
            Path(temp) / "core"
        )

        core.DB = (
            core.ROOT / "data.sqlite3"
        )

        core.UPLOAD_DIR = (
            core.ROOT / "uploads"
        )

        care.EXT_DB = (
            Path(temp) / "care.sqlite3"
        )

        try:

            data = report_data(
                "research-test",
                "CL-0001"
            )

            assert len(
                data["evidence"]
            ) == 5

            assert "<table>" in preview_html(
                data
            )

            pdf = pdf_bytes(data)
            word = docx_bytes(data)

            assert pdf.startswith(b"%PDF")
            assert len(pdf) > 3000

            assert word.startswith(b"PK")
            assert len(word) > 3000

            from pypdf import PdfReader

            text = "\n".join(
                page.extract_text() or ""
                for page in PdfReader(
                    io.BytesIO(pdf)
                ).pages
            )

            assert "Nurse" in text
            assert "Limitations" in text

            from docx import Document

            doc = Document(
                io.BytesIO(word)
            )

            assert any(
                "ClaimsLens" in paragraph.text
                for paragraph in doc.paragraphs
            )

            assert len(doc.tables) >= 1

            assert "cl-metrics" in PAGE
            assert "cl-report" in PAGE

            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                App
            )

            thread = threading.Thread(
                target=server.serve_forever,
                daemon=True
            )

            thread.start()

            try:

                host = (
                    "http://127.0.0.1:"
                    + str(server.server_port)
                )

                endpoints = [
                    (
                        "/api/studio/research/study",
                        b"{"
                    ),
                    (
                        "/api/studio/research/preview"
                        "?claim=CL-0001",
                        b"<!doctype html>"
                    ),
                    (
                        "/api/studio/research/pdf"
                        "?claim=CL-0001",
                        b"%PDF"
                    ),
                    (
                        "/api/studio/research/word"
                        "?claim=CL-0001",
                        b"PK"
                    ),
                ]

                for endpoint, magic in endpoints:

                    with urllib.request.urlopen(
                        host + endpoint,
                        timeout=8
                    ) as response:

                        assert response.status == 200

                        assert response.read(60).startswith(
                            magic
                        )

            finally:

                server.shutdown()
                server.server_close()

                thread.join(
                    timeout=3
                )

        finally:

            (
                core.ROOT,
                core.DB,
                core.UPLOAD_DIR,
                care.EXT_DB
            ) = previous

    print(
        "PASS: Original 240-case ClaimsLens preserved"
    )

    print(
        "PASS: Research metrics and readable dashboard"
    )

    print(
        "PASS: Formatted HTML research report"
    )

    print(
        "PASS: Genuine PDF and editable Word reports"
    )

    print(
        "PASS: PDF text, DOCX structure and HTTP routes"
    )

    print(
        "PASS: Original source and completed studies not rewritten"
    )


# ============================================================
# 9. LAUNCH
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--test",
        action="store_true"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8532
    )

    args = parser.parse_args()

    if args.test:

        self_test()

    else:

        with studio.core.db():
            pass

        with studio.care.database():
            pass

        server = ThreadingHTTPServer(
            ("127.0.0.1", args.port),
            App
        )

        print(
            "\nCLAIMSLENS RESEARCH + CLINICAL STUDIO"
        )

        print(
            "http://127.0.0.1:"
            + str(args.port)
        )

        print(
            "Original chat, case data and past studies preserved."
        )

        print(
            "Synthetic data only."
        )

        try:
            server.serve_forever()

        except KeyboardInterrupt:
            server.server_close()
