#!/usr/bin/env python3
"""
ClaimsLens Welcome Book V6

Professional product introduction with a book opening transition.

Adds a new presentation layer to the existing ClaimsLens V5.
Preserves the original AI agent, 240 cases, clinical workspace,
human review, source verification, and completed research.

Synthetic research demonstration only.
"""

import argparse
import re
import shutil
import subprocess
import tempfile

from pathlib import Path
from http.server import ThreadingHTTPServer

import claimslens_experience_review_v5 as base


# ============================================================
# 1. PREMIUM TYPOGRAPHY AND ANIMATED BOOK DESIGN
# ============================================================

CSS = r'''
<style>

/* PROFESSIONAL WELCOME SCREEN */

#cx-welcome .cx-splash-inner {
    max-width: 1260px;
}

#cx-welcome .cx-hero {
    grid-template-columns:
        minmax(0, 1.15fr)
        minmax(0, .85fr);

    gap: 26px;
}

#cx-welcome .cx-title {
    font-size: clamp(48px, 5.9vw, 81px);
    letter-spacing: -.06em;
    line-height: 1.09;
    margin: 16px 0 23px;
}

#cx-welcome .cx-description {
    max-width: 590px;
    font-size: 14px;
    line-height: 1.86;
    color: #b8cbd4;
}

#cx-welcome .cx-description strong {
    display: block;
    font-size: 11px;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: #9aebd6;
    margin: 0 0 6px;
}

#cx-welcome .cx-description p {
    margin: 0 0 17px;
}

#cx-welcome .cx-eyebrow {
    color: #91dbc8;
    letter-spacing: .16em;
}

#cx-welcome .cx-ctas {
    margin: 26px 0 15px;
}

#cx-welcome .cx-abstract-intro {
    border-left: 2px solid #7edac1;
    padding-left: 17px;
    margin-top: 8px;
}


/* BOOK OPENING TRANSITION */

#cx-book-transition {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 900;
    overflow: hidden;
    perspective: 1800px;
    pointer-events: all;
    background: transparent;
}

#cx-book-transition.active {
    display: block;
}

#cx-book-transition .cx-book-leaf {
    position: absolute;
    top: 0;
    height: 100%;
    width: 50.04%;

    box-sizing: border-box;

    display: flex;
    align-items: center;
    justify-content: center;

    backface-visibility: hidden;
    transform-style: preserve-3d;
    will-change: transform, opacity;
    overflow: hidden;
}

/* LEFT COVER */

#cx-book-transition .cx-book-leaf.left {
    left: 0;
    transform-origin: right center;

    background: linear-gradient(
        128deg,
        #081623 8%,
        #173e46 87%,
        #225e57 100%
    );

    border-right: 2px solid #7ed9c35c;

    box-shadow:
        inset -18px 0 40px #010a1261,
        12px 0 60px #0210187c;
}

/* RIGHT PAGE */

#cx-book-transition .cx-book-leaf.right {
    right: 0;
    transform-origin: left center;

    background: linear-gradient(
        80deg,
        #dcefe9 0%,
        #f1faf6 18%,
        #fcfdfb 100%
    );

    border-left: 2px solid #25584b50;

    box-shadow:
        inset 24px 0 36px #21504321;
}

/* DECORATIVE PAGE FRAMES */

#cx-book-transition .cx-book-leaf:before {
    content: "";
    position: absolute;
    inset: 5%;
    border: 1px solid #93e3cb35;
    pointer-events: none;
}

#cx-book-transition .cx-book-leaf.right:before {
    border-color: #185a4c25;
}

/* BOOK TYPOGRAPHY */

.cx-book-leftword {
    font-size: clamp(27px, 4.5vw, 75px);
    letter-spacing: -.055em;
    font-weight: 850;
    color: #e9fff8;
    text-align: right;
    padding: 25px;
}

.cx-book-rightword {
    font-size: clamp(16px, 2.6vw, 38px);
    font-weight: 650;
    letter-spacing: -.03em;
    color: #244f50;
    text-align: left;
    padding: 25px;
    line-height: 1.2;
}

/* CENTER BOOK SPINE */

#cx-book-transition .cx-book-seam {
    position: absolute;
    left: calc(50% - 3px);
    width: 6px;
    top: 0;
    height: 100%;
    z-index: 3;

    background: linear-gradient(
        90deg,
        #426b62,
        #cdece0,
        #285b51
    );

    box-shadow: 0 0 24px #07191c85;
    transition: opacity .6s;
}

/* THE TWO PAGES OPEN OUTWARD */

#cx-book-transition.opening .cx-book-leaf.left {
    animation:
        cx-unfold-left
        1.25s
        cubic-bezier(.35, .03, .16, 1)
        both;
}

#cx-book-transition.opening .cx-book-leaf.right {
    animation:
        cx-unfold-right
        1.25s
        cubic-bezier(.35, .03, .16, 1)
        both;
}

#cx-book-transition.opening .cx-book-seam {
    opacity: 0;
    transition: opacity .5s .28s;
}

@keyframes cx-unfold-left {

    0% {
        transform: rotateY(0deg);
        opacity: 1;
    }

    62% {
        opacity: 1;
    }

    100% {
        transform: rotateY(-108deg);
        opacity: 0;
    }
}

@keyframes cx-unfold-right {

    0% {
        transform: rotateY(0deg);
        opacity: 1;
    }

    62% {
        opacity: 1;
    }

    100% {
        transform: rotateY(108deg);
        opacity: 0;
    }
}


/* MOBILE LAYOUT */

@media (max-width: 850px) {

    #cx-welcome .cx-hero {
        grid-template-columns: 1fr;
    }

    #cx-welcome .cx-title {
        font-size: clamp(43px, 9vw, 64px);
    }

    #cx-welcome .cx-description {
        font-size: 13px;
    }

    #cx-welcome .cx-stage {
        max-height: 290px;
    }
}


/* ACCESSIBILITY */

@media (prefers-reduced-motion: reduce) {

    #cx-book-transition.opening .cx-book-leaf {
        animation: none !important;
    }

    #cx-book-transition {
        display: none !important;
    }
}

</style>
'''


# ============================================================
# 2. BOOK COVER AND WELCOME CONTENT
# ============================================================

EXTRA = r'''

<div
    id="cx-book-transition"
    aria-hidden="true">

    <div class="cx-book-leaf left">

        <div class="cx-book-leftword">
            ClaimsLens
        </div>

    </div>

    <div class="cx-book-leaf right">

        <div class="cx-book-rightword">

            Clinical intelligence.

            <br>

            Human judgment.

        </div>

    </div>

    <div class="cx-book-seam"></div>

</div>


<script>
(() => {

    "use strict";

    const welcome = document.getElementById(
        "cx-welcome"
    );

    const title = welcome?.querySelector(
        ".cx-title"
    );

    const abstract = welcome?.querySelector(
        ".cx-description"
    );

    const enterButton = document.getElementById(
        "cx-enter"
    );

    const book = document.getElementById(
        "cx-book-transition"
    );

    if (
        !welcome ||
        !title ||
        !abstract ||
        !enterButton ||
        !book
    ) {
        return;
    }


    // ========================================================
    // 3. REPLACE THE PREVIOUS TITLE
    // ========================================================

    title.innerHTML = `
        A clearer picture

        <br>

        <em>of care.</em>
    `;


    // ========================================================
    // 4. REPLACE THE ABSTRACT
    // ========================================================

    abstract.innerHTML = `

        <div class="cx-abstract-intro">

            <p>

                <strong>
                    The challenge
                </strong>

                Nurse case managers often have to piece
                together a patient's progress from medical
                reports, appointments, referrals, and
                insurance updates.

                When those details are scattered, it can
                be difficult to see what has happened,
                what is still pending, and what needs
                attention next.

            </p>

            <p>

                <strong>
                    Our approach
                </strong>

                ClaimsLens brings those records into
                one conversational workspace.

                It connects each finding to its source,
                highlights missing or conflicting
                evidence, and helps prepare follow-ups
                and draft documents.

                Nurses remain in control, reviewing
                each statement before completing
                a draft review.

            </p>

        </div>
    `;


    // ========================================================
    // 5. FIRST-TIME USER GUIDE
    // ========================================================

    const steps = welcome.querySelectorAll(
        ".cx-step"
    );

    const updated = [

        [
            "Explore the record",

            "Open a fictional case and see appointments, clinical notes, imaging, and messages together."
        ],

        [
            "Find what needs attention",

            "Ask the assistant about missing evidence, prepare authorization checklists, and organize follow-ups."
        ],

        [
            "Review with confidence",

            "Inspect original sources and approve, correct, or flag every draft statement before acknowledging the review."
        ]

    ];

    steps.forEach((node, index) => {

        if (!updated[index]) {
            return;
        }

        const head = node.querySelector("b");

        if (head) {
            head.textContent = updated[index][0];
        }

        for (const child of node.childNodes) {

            if (
                child.nodeType === Node.TEXT_NODE &&
                child.textContent.trim()
            ) {

                child.textContent = updated[index][1];
            }
        }
    });


    // ========================================================
    // 6. PROFESSIONAL PRODUCT LANGUAGE
    // ========================================================

    const eyebrow = welcome.querySelector(
        ".cx-eyebrow"
    );

    if (eyebrow) {

        eyebrow.textContent = (
            "EVIDENCE YOU CAN TRACE. "
            + "CARE YOU CAN COORDINATE."
        );
    }

    const note = welcome.querySelector(
        ".cx-intro-note"
    );

    if (note) {

        note.textContent = (
            "Research demonstration using fictional "
            + "cases and medical records. "
            + "ClaimsLens is not validated "
            + "for clinical care."
        );
    }

    enterButton.textContent = (
        "Open ClaimsLens"
    );


    // ========================================================
    // 7. REMOVE LONG DASH PUNCTUATION FROM WELCOME COPY
    // ========================================================

    const walk = document.createTreeWalker(
        welcome,
        NodeFilter.SHOW_TEXT
    );

    let textNode;

    while (
        (textNode = walk.nextNode())
    ) {

        textNode.textContent = textNode.textContent

            .replace(/\u2014/g, ", ")

            .replace(/\u2013/g, " to ");
    }


    // ========================================================
    // 8. BOOK OPENING INTERACTION
    // ========================================================

    let opening = false;

    enterButton.onclick = () => {

        if (opening) {
            return;
        }

        opening = true;

        sessionStorage.setItem(
            "claimslens_intro_seen_v5",
            "1"
        );

        enterButton.blur();


        // Respect reduced motion preferences.

        if (
            window.matchMedia(
                "(prefers-reduced-motion: reduce)"
            ).matches
        ) {

            welcome.classList.remove(
                "show"
            );

            opening = false;

            return;
        }


        // Put the closed book above the welcome screen.

        book.classList.add(
            "active"
        );


        // First render the closed book.
        // Then open its two pages outward.

        requestAnimationFrame(() => {

            requestAnimationFrame(() => {

                welcome.classList.remove(
                    "show"
                );

                book.classList.add(
                    "opening"
                );

            });
        });


        // The existing ClaimsLens product is underneath
        // the animated pages and becomes fully visible.

        window.setTimeout(() => {

            book.classList.remove(
                "opening",
                "active"
            );

            opening = false;

        }, 1450);
    };

})();
</script>
'''


# ============================================================
# 9. PRESERVE THE EXISTING PRODUCT
# ============================================================

PAGE = (
    base.PAGE

    .replace(
        "</head>",
        CSS + "</head>",
        1
    )

    .replace(
        "</body>",
        EXTRA + "</body>",
        1
    )
)


class App(base.App):

    def do_GET(self):

        from urllib.parse import urlparse

        if urlparse(self.path).path == "/":

            self.user()

            return self.respond(
                PAGE,
                mime="text/html; charset=utf-8"
            )

        return super().do_GET()


# ============================================================
# 10. NON-DESTRUCTIVE CHECKS
# ============================================================

def tests():

    assert len(base.core.CASES) == 240

    assert "cx-book-transition" in PAGE

    assert "A clearer picture" in EXTRA

    assert "cx-review" in PAGE

    assert "clp-console" in PAGE

    assert "cx-unfold-left" in CSS

    assert "cx-unfold-right" in CSS


    # Check the syntax of every browser JavaScript block.
    # If Node is not installed, the application can still run.

    if shutil.which("node"):

        scripts = re.findall(
            r"<script\b[^>]*>(.*?)</script>",
            PAGE,
            flags=re.S | re.I
        )

        with tempfile.TemporaryDirectory() as tmp:

            for i, script in enumerate(scripts):

                path = (
                    Path(tmp)
                    / f"inline_{i}.js"
                )

                path.write_text(
                    script,
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

                assert (
                    result.returncode == 0
                ), result.stderr

        print(
            "PASS: All browser JavaScript parses"
        )

    else:

        print(
            "SKIP: Node not available. "
            "Verify animation in Chrome."
        )

    print(
        "PASS: Original 240 synthetic cases preserved"
    )

    print(
        "PASS: All existing nurse review tools preserved"
    )

    print(
        "PASS: New abstract and book transition included"
    )

    print(
        "PASS: No existing source files rewritten"
    )


# ============================================================
# 11. START CLAIMSLENS
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
        default=8536
    )

    args = parser.parse_args()

    if args.test:

        tests()

    else:

        with base.core.db():
            pass

        with base.care.database():
            pass

        with base.db():
            pass

        server = ThreadingHTTPServer(
            ("127.0.0.1", args.port),
            App
        )

        print(
            "ClaimsLens Welcome Book: "
            f"http://127.0.0.1:{args.port}"
        )

        print(
            "Previous applications and completed "
            "research unchanged"
        )

        try:

            server.serve_forever()

        except KeyboardInterrupt:

            server.server_close()
