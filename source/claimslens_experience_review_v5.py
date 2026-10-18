#!/usr/bin/env python3
"""
ClaimsLens Experience & Nurse Review V5.

Additive localhost medical AI research demonstration.
Requires the existing ClaimsLens Clinical Intelligence application.

No real patient data.
No autonomous medical decisions.
No changes to original research source files.
"""

import argparse
import hashlib
import json
import re
import secrets
import sqlite3
import tempfile
import threading
import urllib.request
import http.cookiejar

from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import claimslens_clinical_intelligence as product

core = product.core
care = product.care

REVIEW_DB = (
    Path.home()
    / ".claimslens_nurse_review_v5"
    / "reviews.sqlite3"
)

SOURCE_ID = re.compile(
    r"\bCL-\d{4}-SRC\d{2}\b"
)


# ============================================================
# 1. REVIEW DATABASE
# ============================================================

def clock():
    return datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")


def db():
    REVIEW_DB.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    cx = sqlite3.connect(
        REVIEW_DB,
        timeout=12
    )

    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA foreign_keys=ON")

    cx.executescript("""
    CREATE TABLE IF NOT EXISTS packets (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        claim TEXT NOT NULL,
        fingerprint TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'IN_REVIEW',
        reviewer TEXT,
        created TEXT NOT NULL,
        finalized TEXT
    );

    CREATE INDEX IF NOT EXISTS packets_owner_case
    ON packets(owner,claim,created);

    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        packet TEXT NOT NULL,
        position INTEGER NOT NULL,
        section TEXT NOT NULL,
        body TEXT NOT NULL,
        edited TEXT,
        citation_ids TEXT NOT NULL,
        level TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'PENDING',
        note TEXT NOT NULL DEFAULT '',
        reviewed_at TEXT,
        FOREIGN KEY(packet) REFERENCES packets(id)
    );

    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY,
        packet TEXT NOT NULL,
        item INTEGER,
        action TEXT NOT NULL,
        detail TEXT NOT NULL,
        at TEXT NOT NULL
    );
    """)

    return cx


def rows(cx, query, params=()):
    return [
        dict(x)
        for x in cx.execute(
            query, params
        )
    ]


def get(cx, query, params=()):
    row = cx.execute(
        query, params
    ).fetchone()

    return dict(row) if row else None


# ============================================================
# 2. BUILD SOURCE-LINKED NURSE REVIEW CONTENT
# ============================================================

def capture(owner, claim):

    if claim not in core.CASES:
        raise ValueError(
            "Unknown synthetic claim"
        )

    case = core.CASES[claim]
    decisions = core.evidence(case)

    ncm = care.snapshot(
        owner,
        claim
    )

    notes = ncm.get("notes") or []

    notes = sorted(
        notes,
        key=lambda n: int(n.get("id", 0)),
        reverse=True
    )

    # Capture the information the nurse is reviewing.
    base = {
        "claim": claim,
        "decisions": decisions,
        "risk": ncm.get("risk", {}),
        "authorization": ncm.get(
            "authorization", {}
        ),
        "care": ncm.get("care", []),
        "tasks": ncm.get("tasks", []),
        "notes": notes[:1],
    }

    fingerprint = hashlib.sha256(
        json.dumps(
            base,
            sort_keys=True,
            default=str
        ).encode()
    ).hexdigest()

    items = []

    def add(
        section,
        text,
        ids=(),
        level="CONTEXT"
    ):

        ids = list(
            dict.fromkeys(
                str(x) for x in ids if x
            )
        )

        items.append({
            "section": section,
            "body": str(text)[:1600],
            "citation_ids": ids,
            "level": level,
        })

    add(
        "Case context",

        f"{case['worker']} — {case['title']}; "
        f"injury date {case['date_of_injury']}; "
        f"physician {case['doctor_name']}; "
        f"claim {claim}.",

        (),
        "CASE_METADATA"
    )

    # Use the original ClaimsLens evidence decisions.

    for d in decisions:

        accepted = bool(
            d.get(
                "eligible_for_simulated_closure"
            )
        )

        supporting = (
            d.get("supporting_citations", [])
            if accepted else []
        )

        inspected = (
            d.get("rejection_citations", [])
            if not accepted else []
        )

        if accepted:

            explanation = (
                "Verified by the synthetic evidence rule; "
                "confirm the original report."
            )

        else:

            explanation = (
                "Completion NOT supported. Follow up: "
                + (
                    ", ".join(
                        d.get("blockers", [])
                    )
                    or "qualifying record missing"
                )
                + "."
            )

        add(
            "Care obligations",

            f"{d['label']}: {d['status']}. "
            + explanation,

            supporting or inspected,

            (
                "SUPPORTING_PROOF"
                if accepted
                else "INSPECTION_ONLY"
            )
        )

    # Synthetic risk assessment.

    risk = ncm.get(
        "risk", {}
    )

    add(
        "Risk assessment",

        "Experimental risk score: "
        f"{float(risk.get('score', 0))*100:.1f}%. "
        "Synthetic model only; not a clinical prognosis "
        "or approved triage score.",

        (),
        "SIMULATION"
    )

    # Prior authorization assistance.

    auth = ncm.get(
        "authorization", {}
    )

    if auth.get("missing"):

        auth_explanation = (
            ", ".join(auth["missing"])
            + " still missing."
        )

    else:

        auth_explanation = (
            "Listed criteria collected, but insurer "
            "approval NOT established."
        )

    add(
        "Authorization",

        "Fictional documentation checklist: "
        + auth_explanation,

        (),
        "FICTIONAL_POLICY"
    )

    # Care transitions and discharge barriers.

    for need in ncm.get("care", []):

        add(
            "Care coordination",

            "Discharge / social need: "
            f"{need.get('need', 'unspecified')}; "
            "tracked status "
            f"{need.get('status', 'OPEN')}. "
            "Verify referral suitability and actual "
            "service availability.",

            (),
            "FOLLOW_UP"
        )

    # Nurse worklist.

    for task in ncm.get("tasks", []):

        add(
            "Nurse worklist",

            f"Follow-up: {task.get('title', '')}; "
            "task status "
            f"{task.get('status', 'OPEN')}. "
            "Task closure is not medical completion.",

            (),
            "FOLLOW_UP"
        )

    # Every nonblank line of the latest SOAP draft.

    if notes:

        body = str(
            notes[0].get(
                "body", ""
            )
        )

        for line in body.splitlines():

            line = line.strip()

            if not line:
                continue

            add(
                "SOAP draft · line review",
                line,
                SOURCE_ID.findall(line),
                "DRAFT_NEEDS_REVIEW"
            )

    else:

        add(
            "SOAP draft · line review",

            "No SOAP draft exists yet. Draft one in "
            "the existing clinical workspace before "
            "final nurse review.",

            (),
            "MISSING_DRAFT"
        )

    return fingerprint, items


# ============================================================
# 3. PACKET GENERATION AND PERSISTENCE
# ============================================================

def packet_view(
    cx,
    packet_id,
    owner,
    claim
):

    packet = get(
        cx,
        """SELECT * FROM packets
           WHERE id=? AND owner=? AND claim=?""",
        (
            packet_id,
            owner,
            claim
        )
    )

    if not packet:
        raise ValueError(
            "Review packet not found for this case"
        )

    items = rows(
        cx,
        """SELECT * FROM items
           WHERE packet=?
           ORDER BY position""",
        (packet_id,)
    )

    for item in items:

        item["citation_ids"] = json.loads(
            item["citation_ids"]
        )

    counts = {
        status: sum(
            item["state"] == status
            for item in items
        )
        for status in (
            "PENDING",
            "APPROVED",
            "FLAGGED"
        )
    }

    current = next(
        (
            i
            for i, item in enumerate(items)
            if item["state"] != "APPROVED"
        ),
        len(items)-1
    )

    return {
        "packet": packet,
        "items": items,
        "counts": counts,
        "cursor": current,
        "total": len(items),
        "complete": (
            packet["state"]
            == "REVIEWED_DEMO"
        )
    }


def open_review(
    owner,
    claim,
    force=False
):

    # Starting a review is an explicit user action.
    # If no SOAP exists, create a DRAFT, not a signed note.

    if not care.snapshot(
        owner, claim
    ).get("notes"):

        care.action(
            owner,
            {
                "claim": claim,
                "action": "create_soap"
            }
        )

    fingerprint, content = capture(
        owner,
        claim
    )

    with db() as cx:

        latest = get(
            cx,
            """SELECT * FROM packets
               WHERE owner=? AND claim=?
               ORDER BY rowid DESC
               LIMIT 1""",
            (owner, claim)
        )

        if (
            latest
            and not force
            and latest["state"] == "IN_REVIEW"
            and latest["fingerprint"] == fingerprint
        ):

            return packet_view(
                cx,
                latest["id"],
                owner,
                claim
            )

        packet_id = secrets.token_hex(14)

        cx.execute(
            """INSERT INTO packets
               (id,owner,claim,fingerprint,created)
               VALUES(?,?,?,?,?)""",
            (
                packet_id,
                owner,
                claim,
                fingerprint,
                clock()
            )
        )

        for position, item in enumerate(content):

            cx.execute(
                """INSERT INTO items
                   (packet,position,section,body,
                    citation_ids,level)
                   VALUES(?,?,?,?,?,?)""",

                (
                    packet_id,
                    position,
                    item["section"],
                    item["body"],
                    json.dumps(
                        item["citation_ids"]
                    ),
                    item["level"]
                )
            )

        cx.execute(
            """INSERT INTO events
               (packet,action,detail,at)
               VALUES(?,?,?,?)""",

            (
                packet_id,
                "CREATE",
                "Synthetic review packet created; "
                "not a medical attestation",
                clock()
            )
        )

        cx.commit()

        return packet_view(
            cx,
            packet_id,
            owner,
            claim
        )


# ============================================================
# 4. APPROVE AND NEXT / FLAG / EDIT / FINAL REVIEW
# ============================================================

def review_action(owner, claim, data):

    if claim not in core.CASES:
        raise ValueError(
            "Invalid case"
        )

    packet_id = str(
        data.get("packet", "")
    )

    operation = str(
        data.get("action", "")
    )

    if operation not in (
        "approve",
        "flag",
        "reset",
        "finalize"
    ):

        raise ValueError(
            "Unsupported review action"
        )

    with db() as cx:

        packet = get(
            cx,
            """SELECT * FROM packets
               WHERE id=? AND owner=? AND claim=?""",

            (
                packet_id,
                owner,
                claim
            )
        )

        if not packet:
            raise ValueError(
                "Review packet does not belong "
                "to this case"
            )

        if packet["state"] != "IN_REVIEW":
            raise ValueError(
                "Packet already finalized; "
                "start a new review"
            )

        current_fingerprint, _ = capture(
            owner,
            claim
        )

        if (
            current_fingerprint
            != packet["fingerprint"]
        ):

            raise ValueError(
                "Case data changed after review started. "
                "Start a new review; prior decisions "
                "remain in the audit history."
            )

        if operation == "finalize":

            remaining = get(
                cx,
                """SELECT COUNT(*) AS n
                   FROM items
                   WHERE packet=?
                   AND state!='APPROVED'""",
                (packet_id,)
            )["n"]

            if remaining:

                raise ValueError(
                    f"{remaining} line(s) still "
                    "pending or flagged"
                )

            reviewer = str(
                data.get("reviewer", "")
            ).strip()

            if not 2 <= len(reviewer) <= 80:

                raise ValueError(
                    "Enter reviewer initials/name "
                    "(2–80 characters)"
                )

            cx.execute(
                """UPDATE packets
                   SET state=?, reviewer=?, finalized=?
                   WHERE id=?""",

                (
                    "REVIEWED_DEMO",
                    reviewer,
                    clock(),
                    packet_id
                )
            )

            cx.execute(
                """INSERT INTO events
                   (packet,action,detail,at)
                   VALUES(?,?,?,?)""",

                (
                    packet_id,
                    "FINALIZE",

                    json.dumps({
                        "reviewer": reviewer,
                        "not_clinical_signature": True
                    }),

                    clock()
                )
            )

        else:

            item_id = int(
                data.get("item_id", 0)
            )

            item = get(
                cx,
                """SELECT * FROM items
                   WHERE id=? AND packet=?""",
                (
                    item_id,
                    packet_id
                )
            )

            if not item:

                raise ValueError(
                    "Line does not belong "
                    "to selected packet"
                )

            edited = str(
                data.get(
                    "text",
                    item["body"]
                )
            ).strip()

            if not 1 <= len(edited) <= 1600:

                raise ValueError(
                    "Review text must be "
                    "1–1600 characters"
                )

            note = str(
                data.get("note", "")
            ).strip()

            if len(note) > 800:

                raise ValueError(
                    "Review comment too long"
                )

            if (
                operation == "flag"
                and len(note) < 5
            ):

                raise ValueError(
                    "Explain the concern "
                    "before flagging"
                )

            state = {
                "approve": "APPROVED",
                "flag": "FLAGGED",
                "reset": "PENDING"
            }[operation]

            cx.execute(
                """UPDATE items SET
                   state=?, edited=?, note=?, reviewed_at=?
                   WHERE id=?""",

                (
                    state,

                    (
                        edited
                        if edited != item["body"]
                        else None
                    ),

                    note,

                    (
                        clock()
                        if state != "PENDING"
                        else None
                    ),

                    item_id
                )
            )

            cx.execute(
                """INSERT INTO events
                   (packet,item,action,detail,at)
                   VALUES(?,?,?,?,?)""",

                (
                    packet_id,
                    item_id,
                    operation,

                    json.dumps({
                        "text": edited,
                        "note": note,
                        "review_only": True
                    }),

                    clock()
                )
            )

        cx.commit()

        return packet_view(
            cx,
            packet_id,
            owner,
            claim
        )


# ============================================================
# 5. ORIGINAL SOURCE PREVIEW
# ============================================================

def source_detail(claim, source_id):

    if claim not in core.CASES:
        raise ValueError(
            "Unknown case"
        )

    record = next(
        (
            r
            for r in core.CASES[
                claim
            ]["records"]
            if r["id"] == source_id
        ),
        None
    )

    if not record:

        raise ValueError(
            "Source is not in this synthetic case"
        )

    return {
        "id": record["id"],
        "text": record["text"],
        "event": record["event"],
        "signed": record["signed"],
        "authority": record["authority"],
        "date": record["date"],

        "notice": (
            "Original synthetic record; not "
            "independently clinically validated"
        )
    }


# ============================================================
# 6. PREMIUM VISUAL SYSTEM AND 3D PRODUCT INTRO
# ============================================================

CSS = r'''
<style>

/* ===================== PRODUCT INTRO ===================== */

#cx-welcome {
    position: fixed;
    inset: 0;
    z-index: 500;
    background:
        radial-gradient(
            ellipse at 53% 38%,
            #173b4b 0%,
            #0b1c2b 55%,
            #07111d 100%
        );
    color: #f6fafc;
    display: none;
    overflow: auto;
    font-family: Inter,system-ui,-apple-system,sans-serif;
}

#cx-welcome.show {
    display: block;
    animation: cx-in .55s ease both;
}

#cx-welcome * {
    box-sizing: border-box;
}

@keyframes cx-in {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes cx-rise {
    from {
        opacity: 0;
        transform: translateY(26px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

#cx-sky {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background-image:
        linear-gradient(#ffffff07 1px,transparent 1px),
        linear-gradient(90deg,#ffffff07 1px,transparent 1px);
    background-size: 56px 56px;
    mask-image: linear-gradient(
        #0008,
        transparent 80%
    );
}

.cx-splash-inner {
    position: relative;
    max-width: 1160px;
    margin: auto;
    min-height: 100vh;
    padding: 36px 52px 60px;
    display: flex;
    flex-direction: column;
}

.cx-splash-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 12px;
    letter-spacing: .09em;
    color: #a7c9c9;
}

.cx-brand {
    font-size: 17px;
    color: white;
    font-weight: 850;
    letter-spacing: -.05em;
}

.cx-live {
    border: 1px solid #69cbb76e;
    color: #a2ecd9;
    border-radius: 50px;
    padding: 9px 13px;
    font-weight: 700;
    letter-spacing: .06em;
}

.cx-hero {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 50px;
    align-items: center;
    flex: 1;
    padding: 40px 0;
}

.cx-eyebrow {
    color: #79ddc2;
    letter-spacing: .16em;
    font-size: 11px;
    font-weight: 800;
}

.cx-title {
    font-size: clamp(44px,5.4vw,79px);
    line-height: 1.05;
    letter-spacing: -.065em;
    margin: 16px 0 20px;
    font-weight: 820;
}

.cx-title em {
    font-style: normal;
    background: linear-gradient(
        115deg,
        #b5f9df,
        #64bfc2
    );
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}

.cx-description {
    max-width: 540px;
    color: #b2c9d1;
    line-height: 1.8;
    font-size: 15px;
}

.cx-ctas {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin: 30px 0 22px;
}

.cx-primary,
.cx-secondary {
    border-radius: 11px;
    padding: 15px 23px;
    font-weight: 800;
    cursor: pointer;
    font-size: 13px;
}

.cx-primary {
    border: 1px solid #9af0d0;
    background: linear-gradient(
        115deg,
        #83edcd,
        #4bbaa9
    );
    color: #102c32;
    box-shadow: 0 9px 35px #37b9a23f;
}

.cx-secondary {
    border: 1px solid #ffffff44;
    background: #ffffff0b;
    color: white;
}

.cx-proof {
    display: flex;
    gap: 28px;
    flex-wrap: wrap;
    margin-top: 26px;
    color: #9ab6be;
    font-size: 11px;
}

.cx-proof b {
    color: white;
    font-size: 19px;
    display: block;
    margin-bottom: 5px;
}

/* ====================== 3D EMBLEM ====================== */

.cx-stage {
    position: relative;
    display: grid;
    place-items: center;
    height: 450px;
    perspective: 1100px;
    isolation: isolate;
}

.cx-stage:before {
    content: "";
    position: absolute;
    width: 390px;
    height: 390px;
    border-radius: 50%;
    background: #2fb8a24d;
    filter: blur(94px);
}

.cx-orbit {
    position: absolute;
    width: 360px;
    height: 360px;
    border-radius: 50%;
    border: 1px solid #8ee9cc45;
    transform-style: preserve-3d;
    box-shadow:
        0 0 45px #31dcad14,
        inset 0 0 22px #69dfbd10;
}

.cx-orbit.a {
    animation: cx-orbit-a 11s linear infinite;
}

.cx-orbit.b {
    width: 305px;
    height: 305px;
    border-color: #b1e8f055;
    animation: cx-orbit-b 8s linear infinite;
}

.cx-orbit.c {
    width: 420px;
    height: 420px;
    border-color: #4fbfc727;
    transform: rotateX(64deg);
}

@keyframes cx-orbit-a {
    from {
        transform: rotateX(68deg) rotateZ(0deg);
    }
    to {
        transform: rotateX(68deg) rotateZ(360deg);
    }
}

@keyframes cx-orbit-b {
    from {
        transform: rotateY(64deg) rotateZ(0deg);
    }
    to {
        transform: rotateY(64deg) rotateZ(-360deg);
    }
}

.cx-core {
    position: relative;
    width: 235px;
    height: 235px;
    transform-style: preserve-3d;
    animation: cx-float 5s ease-in-out infinite;
    background: linear-gradient(
        145deg,
        #183e50bb,
        #225b5b88
    );
    border: 1px solid #b9f4d879;
    border-radius: 52px;
    display: grid;
    place-items: center;
    box-shadow:
        inset 0 0 45px #7bffe525,
        0 30px 70px #04131c93;
}

.cx-core:before,
.cx-core:after {
    content: "";
    position: absolute;
    inset: 20px;
    border: 1px solid #9fecc04d;
    border-radius: 38px;
    transform: translateZ(-22px);
}

.cx-core:after {
    inset: 38px;
    transform: translateZ(18px);
    border-color: #dcfff99c;
}

.cx-monogram {
    font-size: 130px;
    line-height: 1;
    font-weight: 900;
    letter-spacing: -.15em;
    margin-right: 26px;
    background: linear-gradient(
        160deg,
        #e6fff6,
        #7bd9c5
    );
    background-clip: text;
    -webkit-background-clip: text;
    color: transparent;
    text-shadow: 0 10px 32px #54d5bd34;
    transform: translateZ(40px);
}

@keyframes cx-float {
    0%,100% {
        transform:
            translateY(-9px)
            rotateY(-18deg)
            rotateX(9deg);
    }
    50% {
        transform:
            translateY(13px)
            rotateY(18deg)
            rotateX(-5deg);
    }
}

.cx-floating-label {
    position: absolute;
    bottom: 21px;
    text-align: center;
    color: #a3d6d1;
    font-size: 11px;
    letter-spacing: .14em;
}

/* ==================== INTRODUCTION ==================== */

.cx-how {
    border-top: 1px solid #ffffff21;
    padding-top: 22px;
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap: 17px;
}

.cx-step {
    border: 1px solid #ffffff1d;
    background: #ffffff08;
    border-radius: 12px;
    padding: 16px;
    color: #a6bfc7;
    font-size: 12px;
    line-height: 1.65;
}

.cx-step b {
    display: block;
    color: #f2fffc;
    font-size: 13px;
    margin-bottom: 6px;
}

.cx-index {
    color: #74d8bb;
    letter-spacing: .12em;
    font-size: 10px;
}

.cx-intro-note {
    margin: 22px 0 0;
    color: #8ea6b0;
    font-size: 11px;
}

/* ===================== NURSE REVIEW ===================== */

#cx-review-backdrop {
    position: fixed;
    inset: 0;
    background: #071821c7;
    backdrop-filter: blur(8px);
    z-index: 590;
    display: none;
}

#cx-review-backdrop.show {
    display: block;
}

#cx-review {
    position: fixed;
    inset: 3vh 4vw;
    background: #f5f8fa;
    color: #213847;
    z-index: 591;
    border-radius: 18px;
    box-shadow: 0 30px 110px #0008;
    display: none;
    flex-direction: column;
    overflow: hidden;
    font-family: Inter,system-ui,sans-serif;
}

#cx-review.show {
    display: flex;
}

.cx-review-head {
    background: #102b40;
    color: #f4fcff;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 18px 26px;
    gap: 12px;
}

.cx-review-head small {
    color: #8dbdb8;
    display: block;
    letter-spacing: .1em;
    font-size: 10px;
}

.cx-review-head b {
    font-size: 22px;
    letter-spacing: -.04em;
}

.cx-review-head button {
    border: 1px solid #ffffff53;
    background: #ffffff13;
    color: white;
    padding: 9px 14px;
    border-radius: 8px;
    cursor: pointer;
}

.cx-progress {
    height: 5px;
    background: #d9e7ec;
}

.cx-progress div {
    height: 100%;
    background: linear-gradient(
        90deg,
        #248b7d,
        #81dcc1
    );
    width: 0%;
    transition: width .35s;
}

.cx-review-main {
    display: grid;
    grid-template-columns:
        minmax(0,1.3fr)
        minmax(280px,.7fr);
    gap: 17px;
    padding: 22px;
    overflow: auto;
    flex: 1;
}

.cx-panel {
    background: white;
    border: 1px solid #dbe5ea;
    border-radius: 13px;
    padding: 23px;
    min-width: 0;
}

.cx-review-label {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .08em;
    color: #618196;
}

.cx-review-number {
    font-size: 27px;
    font-weight: 800;
    letter-spacing: -.04em;
    margin: 8px 0 18px;
}

#cx-line-text {
    display: block;
    width: 100%;
    min-height: 230px;
    padding: 17px;
    font: 15px/1.8 system-ui;
    border: 1px solid #d4e3e8;
    border-radius: 11px;
    resize: vertical;
    color: #1c3c4b;
    background: #fcfefe;
}

#cx-review-note {
    width: 100%;
    margin: 10px 0;
    padding: 12px;
    border: 1px solid #d4e3e8;
    border-radius: 9px;
    min-height: 60px;
}

.cx-warning {
    padding: 12px;
    border-radius: 9px;
    background: #fff4df;
    color: #805c25;
    font-size: 12px;
    line-height: 1.65;
    margin: 12px 0;
}

.cx-review-buttons {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
    margin-top: 15px;
}

.cx-review-buttons button {
    border: 1px solid #c9dbe0;
    background: #edf4f6;
    border-radius: 9px;
    padding: 11px 15px;
    cursor: pointer;
    color: #24495c;
    font-weight: 740;
}

.cx-review-buttons button.primary {
    background: #0b7062;
    color: white;
    border-color: #0b7062;
}

.cx-src {
    display: inline-block;
    margin: 4px;
    padding: 8px 10px;
    border: 1px solid #b9dacf;
    background: #eaf8f2;
    color: #126657;
    border-radius: 8px;
    cursor: pointer;
    font: 11px ui-monospace,monospace;
}

.cx-review-meta {
    font-size: 12px;
    color: #607c88;
    line-height: 1.8;
}

.cx-review-status {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 16px;
}

.cx-chip {
    background: #edf4f7;
    color: #365c6b;
    font-size: 11px;
    padding: 7px 9px;
    border-radius: 7px;
    font-weight: 740;
}

#cx-evidence-view {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    background: #f2f7f8;
    border: 1px solid #e1ecef;
    padding: 15px;
    border-radius: 10px;
    min-height: 115px;
    font: 12px/1.6 ui-monospace,monospace;
}

.cx-review-footer {
    background: white;
    border-top: 1px solid #e0e9eb;
    padding: 13px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.cx-review-footer input {
    max-width: 230px;
    padding: 10px;
    border: 1px solid #c9dbe0;
    border-radius: 9px;
}

.cx-review-footer button {
    border: 0;
    border-radius: 9px;
    padding: 11px 16px;
    background: #173f52;
    color: white;
    font-weight: 800;
    cursor: pointer;
}

.cx-review-footer button:disabled {
    opacity: .5;
    cursor: not-allowed;
}

#cx-review-toast {
    position: fixed;
    z-index: 600;
    bottom: 20px;
    right: 24px;
    background: #142f42;
    color: white;
    padding: 13px 18px;
    border-radius: 10px;
    display: none;
    box-shadow: 0 12px 35px #0004;
}

/* ===================== RESPONSIVE ===================== */

@media(max-width:820px) {

    .cx-splash-inner {
        padding: 24px;
    }

    .cx-hero {
        grid-template-columns: 1fr;
        gap: 0;
    }

    .cx-stage {
        height: 280px;
        order: -1;
    }

    .cx-orbit {
        width: 250px;
        height: 250px;
    }

    .cx-orbit.b {
        width: 215px;
        height: 215px;
    }

    .cx-orbit.c {
        width: 280px;
        height: 280px;
    }

    .cx-core {
        width: 160px;
        height: 160px;
        border-radius: 32px;
    }

    .cx-monogram {
        font-size: 91px;
    }

    .cx-how {
        grid-template-columns: 1fr;
    }

    .cx-title {
        font-size: 43px;
    }

    .cx-review-main {
        grid-template-columns: 1fr;
        padding: 10px;
    }

    .cx-review-head {
        padding: 14px;
    }

    .cx-review-footer {
        flex-wrap: wrap;
    }

    .cx-review-footer input {
        max-width: 100%;
    }
}

@media(prefers-reduced-motion:reduce) {

    .cx-orbit,
    .cx-core {
        animation: none !important;
    }

    #cx-welcome.show {
        animation: none;
    }
}

</style>
'''


# ============================================================
# 7. INTRO SCREEN + LINE-BY-LINE REVIEW INTERFACE
# ============================================================

UI = r'''

<div
    id="cx-welcome"
    aria-label="ClaimsLens introduction"
    role="dialog"
    aria-modal="true">

    <div id="cx-sky"></div>

    <div class="cx-splash-inner">

        <div class="cx-splash-nav">

            <div class="cx-brand">
                ◈ CLAIMSLENS

                <span style="font-weight:400;color:#86b8b5">
                    / Clinical Intelligence
                </span>
            </div>

            <span class="cx-live">
                RESEARCH EDITION · SYNTHETIC ONLY
            </span>

        </div>

        <div class="cx-hero">

            <div style="animation:cx-rise .7s ease both">

                <div class="cx-eyebrow">
                    EVIDENCE-CONSTRAINED MEDICAL AI
                </div>

                <h1 class="cx-title">
                    Clinical clarity.

                    <br>

                    <em>Without the guesswork.</em>
                </h1>

                <p class="cx-description">
                    ClaimsLens is a conversational medical-record
                    intelligence workspace built for nurse case
                    management research. It connects clinical
                    timelines, source-verified obligations,
                    prior-authorization preparation, discharge
                    follow-ups, and reviewable documentation—while
                    keeping the nurse in control of every decision.
                </p>

                <div class="cx-ctas">

                    <button
                        id="cx-enter"
                        class="cx-primary">
                        Enter ClaimsLens →
                    </button>

                    <button
                        id="cx-tour"
                        class="cx-secondary">
                        How it works ↓
                    </button>

                </div>

                <div class="cx-proof">

                    <div>
                        <b>240</b>
                        fictional case records
                    </div>

                    <div>
                        <b>1,200</b>
                        tracked obligations
                    </div>

                    <div>
                        <b>Human review</b>
                        before release
                    </div>

                </div>

            </div>

            <div
                class="cx-stage"
                aria-label="Animated rotating ClaimsLens 3D monogram">

                <div class="cx-orbit a"></div>
                <div class="cx-orbit b"></div>
                <div class="cx-orbit c"></div>

                <div class="cx-core">
                    <span class="cx-monogram">C</span>
                </div>

                <div class="cx-floating-label">
                    CLINICAL EVIDENCE · HUMAN ASSURANCE
                </div>

            </div>

        </div>

        <div id="cx-how" class="cx-how">

            <div class="cx-step">

                <div class="cx-index">
                    01 / EXPLORE
                </div>

                <b>Open a synthetic clinical case</b>

                Navigate 240 claims, appointments,
                correspondence, imaging and original records.

            </div>

            <div class="cx-step">

                <div class="cx-index">
                    02 / REASON
                </div>

                <b>Ask, verify and prepare</b>

                Use the conversational agent to inspect
                source citations, draft authorizations
                and organize nurse follow-ups.

            </div>

            <div class="cx-step">

                <div class="cx-index">
                    03 / REVIEW
                </div>

                <b>Approve each draft line</b>

                Inspect the underlying source,
                edit or flag the statement, and
                advance line by line. Nothing is
                automatically signed or closed.

            </div>

        </div>

        <p class="cx-intro-note">
            Demonstration environment. All patients, source
            records, payer rules, and risk scores are fictional.
            Not approved for clinical use.
        </p>

    </div>

</div>


<div id="cx-review-backdrop"></div>

<section
    id="cx-review"
    role="dialog"
    aria-modal="true"
    aria-label="Nurse review workflow">

    <div class="cx-review-head">

        <div>

            <small>
                CLAIMSLENS / NURSE ASSURANCE DESK
            </small>

            <b>Source-by-source review</b>

            <div
                id="cx-review-case"
                style="font-size:11px;color:#a6caca;margin-top:4px">
            </div>

        </div>

        <button id="cx-review-close">
            Close ×
        </button>

    </div>

    <div class="cx-progress">
        <div id="cx-progress-bar"></div>
    </div>

    <div class="cx-review-main">

        <div class="cx-panel">

            <div
                id="cx-review-section"
                class="cx-review-label">
                DOCUMENT REVIEW
            </div>

            <div
                id="cx-review-index"
                class="cx-review-number">
            </div>

            <textarea
                id="cx-line-text"
                aria-label="Statement to review">
            </textarea>

            <label
                class="cx-review-label"
                for="cx-review-note">

                COMMENTS / REASON FOR FLAG

            </label>

            <textarea
                id="cx-review-note"
                placeholder="Add correction context or explain a concern">
            </textarea>

            <div class="cx-warning">

                Approve & Next records that you reviewed
                this draft line. It does NOT verify a
                diagnosis, certify service completion,
                approve treatment, sign a medical note,
                or modify the original record.

            </div>

            <div class="cx-review-buttons">

                <button id="cx-prev">
                    ← Previous
                </button>

                <button
                    class="primary"
                    id="cx-approve">

                    Approve & Next →

                </button>

                <button id="cx-flag">
                    Flag for correction
                </button>

                <button id="cx-next">
                    Next without approval →
                </button>

            </div>

        </div>

        <aside class="cx-panel">

            <div class="cx-review-label">
                REVIEW STATUS
            </div>

            <div
                class="cx-review-status"
                id="cx-review-status">
            </div>

            <div class="cx-review-label">
                SOURCE ATTRIBUTION
            </div>

            <div id="cx-review-sources"></div>

            <h4 style="margin-top:22px">
                Original source preview
            </h4>

            <div id="cx-evidence-view">
                Select a cited record to inspect
                its original synthetic text.
            </div>

            <p class="cx-review-meta">

                Supporting evidence and inspection-only
                references are different. The clinical
                verifier—not this review queue—controls
                obligation state.

            </p>

        </aside>

    </div>

    <div class="cx-review-footer">

        <span
            id="cx-review-count"
            class="cx-review-meta">
        </span>

        <div
            style="display:flex;align-items:center;gap:9px;flex-wrap:wrap">

            <input
                id="cx-reviewer"
                placeholder="Reviewer name or initials">

            <button id="cx-finalize">
                Finish review (demo)
            </button>

        </div>

    </div>

</section>

<div
    id="cx-review-toast"
    role="status">
</div>


<script>
(() => {

    "use strict";

    const $ = id => document.getElementById(id);

    const esc = value =>
        String(value ?? "").replace(
            /[&<>"']/g,
            char => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[char])
        );

    let packet = null;
    let index = 0;
    let ownerCase = "CL-0001";

    const toast = message => {

        const element = $("cx-review-toast");

        element.textContent = message;
        element.style.display = "block";

        clearTimeout(toast.timeout);

        toast.timeout = setTimeout(
            () => {
                element.style.display = "none";
            },
            4200
        );
    };

    const claim = () =>
        $("claim")?.value || "CL-0001";


    // ========================================================
    // INTRODUCTION EXPERIENCE
    // ========================================================

    function enter() {

        sessionStorage.setItem(
            "claimslens_intro_seen_v5",
            "1"
        );

        $("cx-welcome").classList.remove("show");
        $("cx-enter").blur();
    }

    $("cx-enter").onclick = enter;

    $("cx-tour").onclick = () => {

        $("cx-how").scrollIntoView({
            behavior: "smooth",
            block: "center"
        });
    };

    if (
        sessionStorage.getItem(
            "claimslens_intro_seen_v5"
        ) !== "1"
    ) {

        $("cx-welcome").classList.add("show");
    }


    // ========================================================
    // PRODUCT NAVIGATION
    // ========================================================

    function addMenu() {

        const top = document.querySelector(
            ".top .row"
        );

        if (top) {

            const reviewButton = document.createElement(
                "button"
            );

            reviewButton.id = "cx-review-open";
            reviewButton.textContent = "✓ Nurse review";

            reviewButton.style.cssText = (
                "background:#128775;"
                + "color:white;"
                + "font-weight:800;"
                + "border:0;"
                + "border-radius:9px;"
                + "padding:11px"
            );

            reviewButton.onclick = startReview;

            top.prepend(reviewButton);
        }

        const sidebar = document.querySelector(
            ".sidebar"
        );

        if (sidebar) {

            const replay = document.createElement(
                "button"
            );

            replay.textContent = (
                "✦ Replay product introduction"
            );

            replay.onclick = () => {

                $("cx-welcome").classList.add(
                    "show"
                );

                $("cx-welcome").scrollTop = 0;
            };

            sidebar.append(replay);
        }
    }


    // ========================================================
    // HUMAN REVIEW
    // ========================================================

    async function request(url, body) {

        const response = await fetch(
            url,
            {
                method: body ? "POST" : "GET",

                headers: {
                    "Content-Type": "application/json",
                    "X-ClaimsLens-UI": "1"
                },

                body: body
                    ? JSON.stringify(body)
                    : undefined
            }
        );

        const result = await response.json();

        if (!response.ok) {

            throw Error(
                result.error || "Request failed"
            );
        }

        return result;
    }


    async function startReview() {

        try {

            ownerCase = claim();

            packet = await request(
                "/api/review/start",
                {
                    claim: ownerCase
                }
            );

            index = packet.cursor;

            openReview();

        } catch (error) {

            toast(error.message);
        }
    }


    function openReview() {

        $("cx-review-backdrop").classList.add(
            "show"
        );

        $("cx-review").classList.add(
            "show"
        );

        renderReview();
    }


    function closeReview() {

        $("cx-review-backdrop").classList.remove(
            "show"
        );

        $("cx-review").classList.remove(
            "show"
        );
    }


    $("cx-review-close").onclick = closeReview;

    $("cx-review-backdrop").onclick = closeReview;


    function renderReview() {

        if (!packet) {
            return;
        }

        const items = packet.items;
        const item = items[index];

        if (!item) {
            return;
        }

        $("cx-review-case").textContent = (
            ownerCase
            + " · "
            + packet.packet.state
            + " · review ID "
            + packet.packet.id.slice(0,8)
        );

        $("cx-review-section").textContent = (
            item.section
            + " · "
            + item.level.replaceAll("_", " ")
        );

        $("cx-review-index").textContent = (
            "Statement "
            + (index + 1)
            + " of "
            + items.length
        );

        $("cx-line-text").value = (
            item.edited ?? item.body
        );

        $("cx-review-note").value = (
            item.note ?? ""
        );

        const approved = packet.counts.APPROVED;

        $("cx-progress-bar").style.width = (
            (100 * approved / items.length).toFixed(1)
            + "%"
        );

        $("cx-review-status").innerHTML = `
            <span class="cx-chip">
                ${approved} approved
            </span>

            <span class="cx-chip">
                ${packet.counts.FLAGGED} flagged
            </span>

            <span class="cx-chip">
                ${packet.counts.PENDING} pending
            </span>

            <span class="cx-chip">
                This line: ${esc(item.state)}
            </span>
        `;

        const sources = item.citation_ids;

        $("cx-review-sources").innerHTML = (
            sources.length

            ? sources.map(
                id => `
                    <button
                        class="cx-src"
                        data-cx-source="${esc(id)}">

                        ${esc(id)} ↗

                    </button>
                `
            ).join("")

            : `<p class="cx-review-meta">
                No qualifying source identifier
                for this draft statement.
              </p>`
        );

        document.querySelectorAll(
            "[data-cx-source]"
        ).forEach(button => {

            button.onclick = async () => {

                try {

                    const source = await request(
                        "/api/review/source"
                        + "?claim="
                        + encodeURIComponent(ownerCase)
                        + "&id="
                        + encodeURIComponent(
                            button.dataset.cxSource
                        )
                    );

                    $("cx-evidence-view").textContent = (
                        source.id
                        + "\n"
                        + source.authority
                        + " / "
                        + source.event
                        + "\nSigned: "
                        + source.signed
                        + "\n"
                        + source.date
                        + "\n\n"
                        + source.text
                    );

                } catch (error) {

                    $("cx-evidence-view").textContent = (
                        error.message
                    );
                }
            };
        });

        $("cx-evidence-view").textContent = (
            "Select a source to inspect "
            + "the underlying fictional record."
        );

        $("cx-prev").disabled = index === 0;

        $("cx-next").disabled = (
            index === items.length - 1
        );

        $("cx-review-count").textContent = (
            approved
            + " / "
            + items.length
            + " statements reviewed"
        );

        $("cx-approve").disabled = packet.complete;
        $("cx-flag").disabled = packet.complete;

        $("cx-finalize").disabled = (
            packet.complete
            || approved !== items.length
        );

        if (packet.complete) {

            $("cx-review-count").textContent = (
                "Review complete — demo acknowledgment only; "
                + "not a clinical signature."
            );
        }
    }


    async function doAction(action) {

        try {

            const item = packet.items[index];

            packet = await request(
                "/api/review/action",

                {
                    claim: ownerCase,
                    packet: packet.packet.id,
                    item_id: item.id,

                    action: action,

                    text: $("cx-line-text").value,
                    note: $("cx-review-note").value
                }
            );

            if (
                action === "approve"
                && index < packet.items.length-1
            ) {

                index++;
            }

            renderReview();

            toast(
                action === "approve"
                ? "Line reviewed and saved"
                : "Flag saved for correction"
            );

        } catch (error) {

            toast(error.message);
        }
    }


    // ========================================================
    // BUTTON ACTIONS
    // ========================================================

    $("cx-prev").onclick = () => {

        index = Math.max(
            0,
            index - 1
        );

        renderReview();
    };


    $("cx-next").onclick = () => {

        index = Math.min(
            packet.items.length-1,
            index + 1
        );

        renderReview();
    };


    $("cx-approve").onclick = () => {
        doAction("approve");
    };


    $("cx-flag").onclick = () => {
        doAction("flag");
    };


    $("cx-finalize").onclick = async () => {

        try {

            packet = await request(
                "/api/review/action",

                {
                    claim: ownerCase,
                    packet: packet.packet.id,
                    action: "finalize",
                    reviewer: $("cx-reviewer").value
                }
            );

            renderReview();

            toast(
                "All draft lines reviewed. "
                + "No clinical signature or medical closure "
                + "was recorded."
            );

        } catch (error) {

            toast(error.message);
        }
    };


    // Cmd+Enter or Ctrl+Enter approves the current line.

    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Escape"
                && $("cx-review").classList.contains(
                    "show"
                )
            ) {

                closeReview();
            }

            if (
                (event.metaKey || event.ctrlKey)
                && event.key === "Enter"
                && $("cx-review").classList.contains(
                    "show"
                )
                && !packet.complete
            ) {

                event.preventDefault();
                doAction("approve");
            }
        }
    );

    addMenu();

})();
</script>
'''


# ============================================================
# 8. PRESERVE EXISTING CHAT AND CLINICAL COMMAND CENTER
# ============================================================

PAGE = (
    product.PAGE
    .replace(
        "</head>",
        CSS + "</head>",
        1
    )
    .replace(
        "</body>",
        UI + "</body>",
        1
    )
)


# ============================================================
# 9. NEW REVIEW API ENDPOINTS
# ============================================================

class App(product.App):

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

        if path == "/api/review/source":

            self.user()

            query = parse_qs(
                urlparse(
                    self.path
                ).query
            )

            try:

                return self.respond(
                    source_detail(
                        query.get(
                            "claim", [""]
                        )[0],

                        query.get(
                            "id", [""]
                        )[0]
                    )
                )

            except ValueError as error:

                return self.error(
                    error,
                    422
                )

        if path == "/api/review/status":

            owner = self.user()

            query = parse_qs(
                urlparse(
                    self.path
                ).query
            )

            claim = query.get(
                "claim", [""]
            )[0]

            with db() as cx:

                packet = get(
                    cx,
                    """SELECT * FROM packets
                       WHERE owner=? AND claim=?
                       ORDER BY rowid DESC
                       LIMIT 1""",
                    (
                        owner,
                        claim
                    )
                )

                if packet:

                    result = packet_view(
                        cx,
                        packet["id"],
                        owner,
                        claim
                    )

                else:

                    result = {
                        "packet": None,
                        "items": []
                    }

                return self.respond(result)

        return super().do_GET()


    def do_POST(self):

        path = urlparse(
            self.path
        ).path

        if path not in (
            "/api/review/start",
            "/api/review/action"
        ):

            return super().do_POST()

        owner = self.user()

        if (
            self.headers.get(
                "X-ClaimsLens-UI"
            ) != "1"
        ):

            return self.error(
                "Local UI header required",
                403
            )

        origin = self.headers.get(
            "Origin", ""
        )

        if (
            origin
            and urlparse(origin).netloc
            != self.headers.get("Host", "")
        ):

            return self.error(
                "Cross-origin request blocked",
                403
            )

        try:

            size = int(
                self.headers.get(
                    "Content-Length", "-1"
                )
            )

            if not 1 <= size <= 12000:

                raise ValueError(
                    "Invalid request size"
                )

            data = json.loads(
                self.rfile.read(size)
            )

            if not isinstance(data, dict):

                raise ValueError(
                    "Expected JSON object"
                )

            claim = str(
                data.get("claim", "")
            )

            if path.endswith("/start"):

                return self.respond(
                    open_review(
                        owner,
                        claim,
                        bool(data.get("new"))
                    )
                )

            return self.respond(
                review_action(
                    owner,
                    claim,
                    data
                )
            )

        except (
            ValueError,
            TypeError,
            KeyError,
            sqlite3.Error
        ) as error:

            return self.error(
                error,
                422
            )


# ============================================================
# 10. AUTOMATED TESTS
# ============================================================

def self_test():

    global REVIEW_DB

    assert len(core.CASES) == 240

    # Confirm the previous citation adapter still separates
    # supporting and rejection/inspection references.

    for case in core.CASES.values():

        for decision in core.evidence(case):

            supporting = set(
                decision.get(
                    "supporting_citations", []
                )
            )

            inspection = set(
                decision.get(
                    "rejection_citations", []
                )
            )

            assert not (
                supporting & inspection
            )

    previous = (
        REVIEW_DB,
        core.ROOT,
        core.DB,
        core.UPLOAD_DIR,
        care.EXT_DB
    )

    with tempfile.TemporaryDirectory(
        prefix="cl_review_v5_"
    ) as directory:

        root = Path(directory)

        REVIEW_DB = (
            root / "review.sqlite3"
        )

        core.ROOT = (
            root / "core"
        )

        core.DB = (
            core.ROOT / "db.sqlite3"
        )

        core.UPLOAD_DIR = (
            core.ROOT / "uploads"
        )

        care.EXT_DB = (
            root / "care.sqlite3"
        )

        try:

            owner = "review-tester"
            claim = "CL-0001"

            # Prepare a synthetic SOAP draft through the
            # existing Nurse Case Manager action.

            care.action(
                owner,
                {
                    "claim": claim,
                    "action": "create_soap"
                }
            )

            created = open_review(
                owner,
                claim
            )

            assert created["total"] >= 8

            assert (
                created["counts"]["PENDING"]
                == created["total"]
            )

            assert any(
                item["section"].startswith(
                    "SOAP"
                )
                for item in created["items"]
            )

            packet_id = (
                created["packet"]["id"]
            )

            original_decisions = [
                x["eligible_for_simulated_closure"]
                for x in core.evidence(
                    core.CASES[claim]
                )
            ]

            # Another user must not approve this packet.

            try:

                review_action(
                    "other-user",
                    claim,
                    {
                        "packet": packet_id,
                        "action": "approve",
                        "item_id": created["items"][0]["id"]
                    }
                )

            except ValueError:
                pass

            else:

                raise AssertionError(
                    "Cross-user review unexpectedly authorized"
                )

            # Flag a line.

            first_item = created["items"][0]

            flagged = review_action(
                owner,
                claim,
                {
                    "packet": packet_id,
                    "item_id": first_item["id"],
                    "action": "flag",
                    "note": "Needs supporting context"
                }
            )

            assert (
                flagged["counts"]["FLAGGED"]
                == 1
            )

            # Cannot finalize with unresolved lines.

            try:

                review_action(
                    owner,
                    claim,
                    {
                        "packet": packet_id,
                        "action": "finalize",
                        "reviewer": "RN Test"
                    }
                )

            except ValueError:
                pass

            else:

                raise AssertionError(
                    "Finalized an incomplete review"
                )

            # Approve each line individually.

            for item in created["items"]:

                review_action(
                    owner,
                    claim,
                    {
                        "packet": packet_id,
                        "item_id": item["id"],
                        "action": "approve",
                        "text": item["body"]
                    }
                )

            # Final acknowledgment.

            completed = review_action(
                owner,
                claim,
                {
                    "packet": packet_id,
                    "action": "finalize",
                    "reviewer": "RN Test"
                }
            )

            assert completed["complete"]

            assert (
                completed["counts"]["APPROVED"]
                == completed["total"]
            )

            # Approval cannot alter original medical evidence.

            assert original_decisions == [
                x["eligible_for_simulated_closure"]
                for x in core.evidence(
                    core.CASES[claim]
                )
            ]

            with db() as cx:

                events = rows(
                    cx,
                    """SELECT id FROM events
                       WHERE packet=?""",
                    (packet_id,)
                )

                assert len(events) >= (
                    completed["total"] + 2
                )

            assert source_detail(
                claim,
                "CL-0001-SRC02"
            )["id"] == "CL-0001-SRC02"

            # Real HTTP smoke test.

            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                App
            )

            thread = threading.Thread(
                target=server.serve_forever,
                daemon=True
            )

            thread.start()

            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(
                    http.cookiejar.CookieJar()
                )
            )

            base = (
                "http://127.0.0.1:"
                + str(server.server_port)
            )

            try:

                with opener.open(
                    base + "/",
                    timeout=8
                ) as response:

                    assert (
                        b"cx-welcome"
                        in response.read()
                    )

                request = urllib.request.Request(
                    base + "/api/review/start",

                    data=json.dumps({
                        "claim": "CL-0002"
                    }).encode(),

                    method="POST",

                    headers={
                        "Content-Type": "application/json",
                        "X-ClaimsLens-UI": "1"
                    }
                )

                with opener.open(
                    request,
                    timeout=8
                ) as response:

                    packet = json.load(response)

                    assert packet["total"] >= 8

                assert (
                    packet["packet"]["claim"]
                    == "CL-0002"
                )

            finally:

                server.shutdown()
                server.server_close()

                thread.join(timeout=3)

        finally:

            (
                REVIEW_DB,
                core.ROOT,
                core.DB,
                core.UPLOAD_DIR,
                care.EXT_DB
            ) = previous

    print(
        "PASS: Original 240-case application and citation separation"
    )

    print(
        "PASS: Individual draft-line review and saved decisions"
    )

    print(
        "PASS: Flag, edit, approve and audit trail"
    )

    print(
        "PASS: Incomplete reviews cannot be finalized"
    )

    print(
        "PASS: Review ownership and case isolation"
    )

    print(
        "PASS: Medical obligation states remain unchanged"
    )

    print(
        "PASS: Product introduction and review HTTP endpoints"
    )

    print(
        "PASS: Original source and research files not rewritten"
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
        default=8535
    )

    args = parser.parse_args()

    if args.test:

        self_test()

    else:

        with core.db():
            pass

        with care.database():
            pass

        with db():
            pass

        server = ThreadingHTTPServer(
            ("127.0.0.1", args.port),
            App
        )

        print(
            "\nCLAIMSLENS EXPERIENCE + HUMAN REVIEW"
        )

        print(
            f"http://127.0.0.1:{args.port}"
        )

        print(
            "Animated welcome screen, clinical command "
            "center and nurse approval queue enabled."
        )

        print(
            "Synthetic only. Previous applications and "
            "completed research unchanged."
        )

        try:

            server.serve_forever()

        except KeyboardInterrupt:

            server.server_close()
