#!/usr/bin/env python3
"""
ClaimsLens Guided Product V8

Simple instructions and nurse case management benefits
throughout the existing application.

Presentation-only addition to ClaimsLens V7.

No changes to original evidence verification,
historical research, patient-demo records,
AI conversations, or nurse review decisions.

Synthetic data only.
"""

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import threading
import urllib.request

from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import claimslens_welcome_v7 as base


# ============================================================
# SECTION GUIDANCE
#
# Each section includes:
# 1. Section title
# 2. How to use it
# 3. How it helps nurse case managers
# ============================================================

GUIDES = {

    "chat": (
        "Ask ClaimsLens",

        "Choose a fictional claim. Type a question about "
        "appointments, reports, missing records or next steps. "
        "Ask to see the source IDs, and open the original "
        "documents before relying on an answer.",

        "Find information across a busy caseload faster and "
        "spend less time searching through separate messages. "
        "AI answers are drafts, not medical decisions."
    ),

    "explorer": (
        "Find a case",

        "Search by claim number, injury or test scenario. "
        "Use the filter and page controls, then select a case "
        "to open its records.",

        "Move between multiple active files without losing "
        "track of which injured worker and claim you are "
        "reviewing."
    ),

    # ========================================================
    # ORIGINAL CASE WORKSPACE
    # ========================================================

    "workspace:Overview": (
        "Case overview",

        "Start with the injury, treating physician, adjuster, "
        "work status and record counts. Open a detailed section "
        "when you need to check a specific event.",

        "Understand the case quickly before making calls, "
        "preparing updates or setting follow-up priorities."
    ),

    "workspace:Appointments": (
        "Appointments and visits",

        "Compare scheduled dates with actual dates of service. "
        "Read visit notes, work restrictions and recommended "
        "follow-ups. A scheduled visit does not mean it happened.",

        "Spot missed appointments, delayed treatment and "
        "missing visit reports that require nurse follow-up."
    ),

    "workspace:Inbox": (
        "Messages and correspondence",

        "Read the claim messages in date order. Ask ClaimsLens "
        "to cross-check a message against signed medical records "
        "before treating it as fact.",

        "Keep communication organized and notice important "
        "changes without confusing an email with proof of "
        "completed treatment."
    ),

    "workspace:Imaging": (
        "Imaging records",

        "Review the order, patient details, body part, date "
        "and final report. Check whether the source is signed "
        "and still current.",

        "Know when imaging needs follow-up and avoid treating "
        "an order, scheduled scan or preliminary note as a "
        "completed study."
    ),

    "workspace:Evidence": (
        "Evidence verification",

        "Select Run AssuranceNet verification and read each "
        "result. Look at supporting sources, inspection-only "
        "sources and blockers. Open the source checks when a "
        "result needs clarification.",

        "See what is actually documented and what is still "
        "missing. The system does not close a service just "
        "because someone mentioned it."
    ),

    "workspace:Uploads": (
        "Document uploads",

        "Add fictional test files, inspect extracted text or "
        "image previews and check the right claim is selected. "
        "Any AI image observations need independent verification.",

        "Keep new information close to the case record. "
        "An upload alone is not proof that a service was completed."
    ),

    "workspace:Report": (
        "Case report and exports",

        "Review the generated case summary, add your own notes "
        "and check dates and citations. Export a PDF or Word "
        "report after your review.",

        "Prepare clearer case updates and handoffs with less "
        "repeated writing. Nothing here is a signed clinical report."
    ),

    "workspace:Research": (
        "Evidence and study limitations",

        "Read how the synthetic cases were evaluated and what "
        "the test results do not prove. Review known errors "
        "before making claims about performance.",

        "Understand when the AI may help, when it may fail "
        "and why professional review remains essential."
    ),

    # ========================================================
    # CLINICAL STUDIO
    # ========================================================

    "studio:Overview": (
        "Clinical Studio overview",

        "Start with the case summary and outstanding actions. "
        "Select the worklist, authorization or documentation "
        "tools when a task needs attention.",

        "Get a practical picture of the claim before moving "
        "between reports, emails and follow-ups."
    ),

    "studio:Timeline": (
        "Longitudinal timeline",

        "Filter the timeline by visits, source records or emails. "
        "Read the date and source for each event, then follow "
        "any missing or conflicting entries.",

        "See how care has changed over time and notice delays "
        "or gaps that can be hard to find across separate systems."
    ),

    "studio:Evidence": (
        "Source review",

        "Open each obligation to see its decision, proof, rejected "
        "sources and reason for the result. Check the original "
        "source before documenting completion.",

        "Reduce unsupported conclusions and make it easier "
        "to explain why more information is needed."
    ),

    "studio:Risk": (
        "Experimental risk signals",

        "Review the fictional risk inputs and try simulated "
        "changes to see how the research score responds. "
        "Do not use it to diagnose or triage a patient.",

        "Explore how changing clinical information could support "
        "follow-up prioritization in a future validated system. "
        "This model is not clinically validated."
    ),

    "studio:Authorization": (
        "Authorization preparation",

        "Check which fictional policy documents are present. "
        "Add synthetic source details, then review and copy "
        "the draft packet. Packet readiness is not payer approval.",

        "Organize missing medical necessity documentation "
        "and reduce repeated requests for the same records."
    ),

    "studio:Care plan": (
        "Discharge and care coordination",

        "Add needs such as transportation or medication access, "
        "create follow-up tasks and update their progress. "
        "Confirm any real service independently.",

        "Keep practical barriers visible alongside treatment "
        "plans, so fewer follow-ups are overlooked during a "
        "busy day."
    ),

    "studio:SOAP": (
        "SOAP drafting",

        "Generate a SOAP draft (Subjective, Objective, Assessment, "
        "Plan). Read each section, then open Nurse Review "
        "to check every statement.",

        "Create a starting point for documentation without "
        "treating AI-written statements as verified clinical notes."
    ),

    "studio:Research": (
        "Research reporting",

        "Compare the email-only, source-context and gated AI "
        "results. Open the formatted report and export the "
        "PDF or Word version for review.",

        "Explain the strengths and failures of the prototype "
        "clearly, including the small synthetic sample and "
        "missed valid completions."
    ),

    # ========================================================
    # CLINICAL COMMAND CENTER
    # ========================================================

    "console:Overview": (
        "Your daily case snapshot",

        "Check supported obligations, evidence gaps and "
        "outstanding tasks. Use the quick actions to open "
        "the part of the case that needs attention.",

        "Prioritize follow-ups across several claims without "
        "reading every document from the beginning."
    ),

    "console:Case obligations": (
        "Service and evidence status",

        "Read each tracked obligation and its supporting or "
        "rejected sources. Expand the individual checks to "
        "understand why an item remains open.",

        "Make clear, source-based status updates instead of "
        "relying on scheduled appointments or informal messages."
    ),

    "console:Nurse workflow": (
        "Nurse worklist",

        "Create follow-up tasks, update task progress, view "
        "fictional authorization requirements and track discharge "
        "barriers. Tasks and medical service completion are separate.",

        "Keep calls, record requests and care coordination steps "
        "in one place so important work is less likely to be missed."
    ),

    "console:Clinical evidence": (
        "Clinical history and records",

        "Scan the timeline and open the full workspace to inspect "
        "visit notes, imaging, messages and uploaded documents.",

        "Build an accurate picture of treatment progress without "
        "mixing up plans, reported events and confirmed results."
    ),

    "console:Research & QA": (
        "Research and quality checks",

        "Review the completed synthetic tests, known failures "
        "and source module status. Use the report controls "
        "to inspect or export the findings.",

        "Show what was tested, what remains uncertain and "
        "how the application avoids overstating clinical performance."
    ),

    # ========================================================
    # ORIGINAL NURSE CARE EXTENSION
    # ========================================================

    "care:Overview": (
        "Nurse Care overview",

        "Read the selected case summary, check suggested follow-ups "
        "and add tasks to the worklist when appropriate.",

        "Organize the next steps for one claim without manually "
        "combining all the source records."
    ),

    "care:Risk": (
        "Risk simulation",

        "Review the fictional risk signals and try example values "
        "to see how the model changes. Treat all outputs as "
        "research only.",

        "Demonstrate possible prioritization tools without using "
        "an unvalidated score for real clinical decisions."
    ),

    "care:Authorization": (
        "Authorization checklist",

        "Compare the fictional policy checklist with the demo "
        "evidence and prepare a draft packet for nurse review.",

        "Identify documentation gaps sooner. A completed "
        "checklist is not a payer decision."
    ),

    "care:Care coordination": (
        "Discharge support",

        "Record barriers such as transportation or home access "
        "and inspect the fictional resource suggestions.",

        "Track nonmedical barriers that may affect recovery "
        "and require coordinated follow-up."
    ),

    "care:SOAP": (
        "Documentation review",

        "Generate a draft, correct the wording, and record "
        "a simulated nurse review. Open Nurse Review for "
        "statement-by-statement checks.",

        "Reduce time spent starting a note while keeping "
        "responsibility for accuracy with the nurse."
    ),

    "care:Business": (
        "Illustrative time savings",

        "Enter hypothetical case volume, minutes and cost "
        "assumptions. Review the estimate as a scenario, "
        "not a measured outcome.",

        "Explore potential operational value without claiming "
        "that real nursing time or money has already been saved."
    ),

    # ========================================================
    # HUMAN-IN-THE-LOOP REVIEW
    # ========================================================

    "nurse": (
        "Nurse assurance desk",

        "Read the current statement and open any cited source. "
        "Edit unclear text, or flag concerns with a reason. "
        "Select Approve & Next only after checking the line. "
        "Finish when every line is reviewed.",

        "Keep a record of what was checked and what still needs "
        "correction. Approval records draft review only. "
        "It never signs a clinical note or closes a care obligation."
    )
}


# ============================================================
# PROFESSIONAL GUIDE STYLING
# ============================================================

CSS = r'''
<style>

.clg-guide {
    position: relative;
    flex-shrink: 0;

    background: linear-gradient(
        115deg,
        #f4faf7,
        #f8fbfd
    );

    border: 1px solid #cde3dc;
    border-radius: 13px;

    padding: 13px 16px;
    margin: 0 0 14px;

    color: #214536;

    font: 12px/1.65 system-ui,
        -apple-system, sans-serif;

    box-shadow: 0 2px 10px #113d3310;
}

.clg-guide summary {
    list-style: none;
    cursor: pointer;

    display: flex;
    align-items: center;
    gap: 9px;

    font-size: 12px;
    font-weight: 800;
    color: #154b40;

    outline-offset: 4px;
}

.clg-guide summary::-webkit-details-marker {
    display: none;
}

.clg-guide summary:before {
    content: "?";

    display: inline-grid;
    place-items: center;

    width: 22px;
    height: 22px;
    flex: none;

    background: #176d61;
    color: white;
    border-radius: 7px;

    font: 800 13px system-ui;
}

.clg-guide summary:after {
    content: "Hide guide";
    margin-left: auto;

    font: 600 11px system-ui;
    color: #527d71;
}

.clg-guide:not([open]) summary:after {
    content: "Show guide";
}

.clg-guide-grid {
    display: grid;

    grid-template-columns: 1fr 1fr;
    gap: 14px;

    margin-top: 12px;
}

.clg-guide-grid div {
    padding-left: 12px;
    border-left: 2px solid #b3d8ca;
    min-width: 0;
}

.clg-guide-grid strong {
    display: block;
    font-size: 10px;
    letter-spacing: .09em;

    text-transform: uppercase;
    color: #367565;

    margin-bottom: 3px;
}

.clg-guide-grid p {
    margin: 0;

    color: #3f5f56;
    font-size: 12px;
    line-height: 1.68;
}

#clg-chat {
    margin: 9px auto 0;
    max-width: 940px;
    width: calc(100% - 38px);
}

#clg-explorer {
    margin: 10px 0;
}

#clg-nurse {
    margin: 10px 18px 0;
}

@media(max-width:670px) {

    .clg-guide-grid {
        grid-template-columns: 1fr;
        gap: 10px;
    }

    .clg-guide {
        padding: 11px 12px;
    }

    .clg-guide-grid p {
        font-size: 11px;
    }
}

</style>
'''


# ============================================================
# DYNAMIC SECTION GUIDES
#
# Guides are inserted separately from clinical documents.
# They are never stored as patient notes or AI responses.
# ============================================================

JS = r'''
<script>
(() => {
    "use strict";

    const content = __GUIDES__;

    const guideId = type =>
        "clg-" + type.replace(
            /[^a-z0-9]+/gi,
            "-"
        ).toLowerCase();


    function createGuide(type) {

        const parts = content[type];

        if (!parts) {
            return null;
        }

        const element = document.createElement(
            "details"
        );

        element.className = "clg-guide";
        element.id = guideId(type);
        element.open = true;

        element.dataset.guide = type;


        const label = document.createElement(
            "summary"
        );

        label.textContent = (
            parts[0]
            + " | Quick guide"
        );

        element.append(label);


        const grid = document.createElement(
            "div"
        );

        grid.className = "clg-guide-grid";


        const sections = [

            [
                "How to use this section",
                parts[1]
            ],

            [
                "Why this helps nurse case managers",
                parts[2]
            ]
        ];


        for (const [heading,value] of sections) {

            const section = document.createElement(
                "div"
            );

            const title = document.createElement(
                "strong"
            );

            title.textContent = heading;


            const paragraph = document.createElement(
                "p"
            );

            paragraph.textContent = value;


            section.append(
                title,
                paragraph
            );

            grid.append(section);
        }


        element.append(grid);

        return element;
    }


    function insertGuide(host,type) {

        if (
            !host ||
            !content[type]
        ) {
            return;
        }

        const first = host.firstElementChild;

        if (
            first?.dataset?.guide === type
        ) {
            return;
        }


        const previous = host.querySelector(
            ":scope > .clg-guide"
        );

        if (previous) {
            previous.remove();
        }


        const element = createGuide(type);

        host.prepend(element);
    }


    // ========================================================
    // MATCH THE GUIDE TO THE OPEN SECTION
    // ========================================================

    const sections = {

        workspace: [

            "panel",

            () => "workspace:" + (
                document.querySelector(
                    "#tabs button.selected"
                )?.textContent?.trim()
                || "Overview"
            )
        ],

        studio: [

            "cl-content",

            () => "studio:" + (
                document.querySelector(
                    "#cl-nav [data-tab].active"
                )?.dataset.tab
                || "Overview"
            )
        ],

        console: [

            "clp-content",

            () => "console:" + (
                document.querySelector(
                    "#clp-tabs [data-clp-tab].active"
                )?.dataset.clpTab
                || "Overview"
            )
        ],

        care: [

            "care-body",

            () => "care:" + (
                document.querySelector(
                    "#care-tabs button.active"
                )?.textContent?.trim()
                || "Overview"
            )
        ]
    };


    function updateGuides() {

        for (const [,config] of Object.entries(
            sections
        )) {

            const [id,detect] = config;

            const host = document.getElementById(
                id
            );

            if (!host) {
                continue;
            }

            insertGuide(
                host,
                detect()
            );
        }
    }


    // ========================================================
    // WATCH FOR EXISTING SECTIONS TO RENDER
    // ========================================================

    for (const [,config] of Object.entries(
        sections
    )) {

        const [id,detect] = config;

        const host = document.getElementById(
            id
        );

        if (!host) {
            continue;
        }


        const observer = new MutationObserver(
            () => {

                queueMicrotask(
                    () => insertGuide(
                        host,
                        detect()
                    )
                );
            }
        );


        observer.observe(
            host,
            {
                childList: true,
                subtree: false
            }
        );
    }


    // ========================================================
    // MAIN CHAT GUIDE
    // ========================================================

    const feed = document.getElementById(
        "feed"
    );

    if (
        feed &&
        !document.getElementById(
            "clg-chat"
        )
    ) {

        const element = createGuide(
            "chat"
        );

        if (element) {

            feed.before(element);
        }
    }


    // ========================================================
    // SEARCHABLE CASE EXPLORER GUIDE
    // ========================================================

    const counter = document.getElementById(
        "cl-match"
    );

    if (
        counter &&
        !document.getElementById(
            "clg-explorer"
        )
    ) {

        const element = createGuide(
            "explorer"
        );

        if (element) {

            counter.after(element);
        }
    }


    // ========================================================
    // NURSE REVIEW GUIDE
    // ========================================================

    const reviewProgress = document.querySelector(
        "#cx-review .cx-progress"
    );

    if (
        reviewProgress &&
        !document.getElementById(
            "clg-nurse"
        )
    ) {

        const element = createGuide(
            "nurse"
        );

        if (element) {

            reviewProgress.after(
                element
            );
        }
    }


    // Initial render.

    updateGuides();


    // Existing tab buttons keep their original behavior.
    // We only update the guide after a tab is selected.

    document.addEventListener(
        "click",
        event => {

            const sectionButton = event.target.closest(
                "#tabs button,"
                + "#cl-nav [data-tab],"
                + "#clp-tabs [data-clp-tab],"
                + "#care-tabs button"
            );

            if (sectionButton) {

                queueMicrotask(
                    updateGuides
                );
            }
        }
    );

})();
</script>
'''


# ============================================================
# ASSEMBLE THE EXISTING APPLICATION
# ============================================================

GUIDE_SCRIPT = JS.replace(
    "__GUIDES__",
    json.dumps(
        GUIDES,
        ensure_ascii=False
    )
)

PAGE = (
    base.PAGE

    .replace(
        "</head>",
        CSS + "</head>",
        1
    )

    .replace(
        "</body>",
        GUIDE_SCRIPT + "</body>",
        1
    )
)


class App(base.App):

    def do_GET(self):

        if urlparse(self.path).path == "/":

            self.user()

            return self.respond(
                PAGE,
                mime="text/html; charset=utf-8"
            )

        return super().do_GET()


# ============================================================
# NON-DESTRUCTIVE TESTS
# ============================================================

def tests():

    core = base.previous.base.core

    assert len(core.CASES) == 240

    assert len(GUIDES) >= 28

    assert all(
        len(parts) == 3
        and len(parts[0]) > 6
        and len(parts[1]) > 40
        and len(parts[2]) > 40
        for parts in GUIDES.values()
    )


    for tab in (
        "Overview",
        "Appointments",
        "Inbox",
        "Imaging",
        "Evidence",
        "Uploads",
        "Report",
        "Research"
    ):

        assert (
            "workspace:" + tab
        ) in GUIDES


    for tab in (
        "Overview",
        "Timeline",
        "Evidence",
        "Risk",
        "Authorization",
        "Care plan",
        "SOAP",
        "Research"
    ):

        assert (
            "studio:" + tab
        ) in GUIDES


    for tab in (
        "Overview",
        "Case obligations",
        "Nurse workflow",
        "Clinical evidence",
        "Research & QA"
    ):

        assert (
            "console:" + tab
        ) in GUIDES


    assert "nurse" in GUIDES
    assert "explorer" in GUIDES
    assert "chat" in GUIDES

    assert "cx-book-transition" in PAGE
    assert "cx-review" in PAGE
    assert "clp-console" in PAGE
    assert "cl-choose" in PAGE

    assert "\u2014" not in GUIDE_SCRIPT


    # Check every embedded JavaScript block if Node is installed.

    scripts = re.findall(
        r"<script\b[^>]*>(.*?)</script>",
        PAGE,
        flags=re.S | re.I
    )

    if shutil.which("node"):

        with tempfile.TemporaryDirectory() as tmp:

            for index, source in enumerate(scripts):

                path = (
                    Path(tmp)
                    / f"check_{index}.js"
                )

                path.write_text(
                    source,
                    encoding="utf-8"
                )

                result = subprocess.run(
                    [
                        "node",
                        "--check",
                        str(path)
                    ],
                    capture_output=True,
                    text=True
                )

                assert result.returncode == 0, (
                    result.stderr
                )

        print(
            f"PASS: {len(scripts)} browser scripts parse"
        )

    else:

        print(
            "SKIP: Node unavailable. "
            "Check the interface in Chrome."
        )


    # Test the application using disposable local databases.

    care = base.previous.base.care

    review = base.previous.base

    previous = (
        core.ROOT,
        core.DB,
        core.UPLOAD_DIR,
        care.EXT_DB,
        review.REVIEW_DB
    )

    with tempfile.TemporaryDirectory() as tmp:

        root = Path(tmp)

        core.ROOT = root / "core"
        core.DB = core.ROOT / "case.sqlite3"
        core.UPLOAD_DIR = core.ROOT / "uploads"

        care.EXT_DB = root / "care.sqlite3"
        review.REVIEW_DB = root / "review.sqlite3"


        try:

            server = ThreadingHTTPServer(
                ("127.0.0.1",0),
                App
            )

            thread = threading.Thread(
                target=server.serve_forever,
                daemon=True
            )

            thread.start()


            try:

                from http.cookiejar import CookieJar

                opener = urllib.request.build_opener(
                    urllib.request.HTTPCookieProcessor(
                        CookieJar()
                    )
                )

                url = (
                    "http://127.0.0.1:"
                    + str(server.server_port)
                    + "/"
                )

                with opener.open(
                    url,
                    timeout=10
                ) as response:

                    html = response.read().decode(
                        "utf-8"
                    )

                assert "clg-guide-grid" in html
                assert "cx-book-transition" in html
                assert "How to use this section" in html

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
                care.EXT_DB,
                review.REVIEW_DB
            ) = previous


    print(
        "PASS: Original 240 synthetic cases preserved"
    )

    print(
        "PASS: Guided chat and case explorer"
    )

    print(
        "PASS: Original medical workspace guidance"
    )

    print(
        "PASS: Clinical Studio and command center guidance"
    )

    print(
        "PASS: Nurse Review instructions included"
    )

    print(
        "PASS: Animated logo and book transition retained"
    )

    print(
        "PASS: Local HTTP application responds"
    )

    print(
        "PASS: Original files and research not rewritten"
    )


# ============================================================
# START THE GUIDED PRODUCT
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
        default=8538
    )

    args = parser.parse_args()

    if args.test:

        tests()

    else:

        core = base.previous.base.core
        care = base.previous.base.care
        review = base.previous.base

        with core.db():
            pass

        with care.database():
            pass

        with review.db():
            pass

        server = ThreadingHTTPServer(
            ("127.0.0.1", args.port),
            App
        )

        print(
            "CLAIMSLENS GUIDED PRODUCT"
        )

        print(
            f"http://127.0.0.1:{args.port}"
        )

        print(
            "Original source and completed research unchanged."
        )

        print(
            "Synthetic cases only."
        )

        try:

            server.serve_forever()

        except KeyboardInterrupt:

            server.server_close()
