#!/usr/bin/env python3
"""Non-destructive live ClaimsLens citation and chat upgrade.
Original ClaimsLens code and completed research remain untouched.
Synthetic-data prototype only.
"""

import argparse
import json
import re
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse

import claimslens_final as core

ORIGINAL_VERIFY = core.verify
SOURCE_PATTERN = re.compile(r"\bCL-\d{4}-SRC\d{2}\b")


def verified_v2(case, obligation):
    """Separate proof citations from inspection/rejection citations."""
    result = dict(ORIGINAL_VERIFY(case, obligation))
    traces = result.get("traces", [])

    valid_sources = {
        trace["source"]
        for trace in traces
        if not trace.get("failed")
    }

    known_sources = {
        source["id"]
        for source in case["records"]
    }

    accepted = bool(
        result.get("eligible_for_simulated_closure")
    )

    supporting = (
        list(dict.fromkeys(result.get("citations", [])))
        if accepted else []
    )

    # Never weaken the original evidence gate.
    if accepted and (
        not supporting
        or not set(supporting).issubset(
            valid_sources & known_sources
        )
    ):
        accepted = False
        supporting = []
        result["eligible_for_simulated_closure"] = False
        result["status"] = "OPEN - NEEDS REVIEW"
        result["blockers"] = (
            list(result.get("blockers", []))
            + ["INVALID_SUPPORTING_CITATION"]
        )

    inspected = (
        []
        if accepted
        else [
            trace["source"]
            for trace in traces
            if trace["source"] in known_sources
        ]
    )

    result["supporting_citations"] = supporting
    result["rejection_citations"] = list(
        dict.fromkeys(inspected)
    )

    # Backward-compatible field now contains completion proof only.
    result["citations"] = supporting

    result["citation_protocol"] = (
        "V2_SEPARATED_PRODUCT_ADAPTER"
    )

    return result


# Runtime-only patch. Original source on disk is unchanged.
core.verify = verified_v2

import claimslens_care_upgrade as care

# Preserve existing ChatGPT-style page and integrated NCM drawer.
PAGE = care.PAGE

PAGE = PAGE.replace(
    "o.citations.join(', ')",
    "((o.eligible_for_simulated_closure ? "
    "o.supporting_citations : o.rejection_citations)||[]).join(', ')"
).replace(
    "x.citations.join(', ')",
    "((x.eligible_for_simulated_closure ? "
    "x.supporting_citations : x.rejection_citations)||[]).join(', ')"
).replace(
    "Citations: '+",
    "Citations (proof if supported; inspection otherwise): '+"
).replace(
    "Sources: '+",
    "Sources (proof if supported; inspection otherwise): '+"
)


def evidence_summary(claim, question):
    case = core.CASES[claim]
    decisions = core.evidence(case)

    q = question.lower()

    if re.search(
        r"\b(imag|mri|ct|x-ray|xray|scan|radiolog)\w*\b",
        q
    ):
        decisions = [
            d for d in decisions
            if d["kind"] == "IMAGING"
        ]

    elif "authorization" in q or "payer" in q:
        decisions = [
            d for d in decisions
            if d["kind"] == "AUTHORIZATION"
        ]

    elif "specialist" in q or "consult" in q:
        decisions = [
            d for d in decisions
            if d["kind"] == "CONSULT"
        ]

    elif "therapy" in q:
        decisions = [
            d for d in decisions
            if d["kind"] == "THERAPY"
        ]

    output = []

    for decision in decisions:
        supported = decision["supporting_citations"]
        rejected = decision["rejection_citations"]

        output.append(
            f"{decision['label']}: {decision['status']}\n"
            f"Supporting completion sources: "
            f"{', '.join(supported) if supported else 'none'}\n"
            f"Inspection-only sources (NOT proof): "
            f"{', '.join(rejected) if rejected else 'none'}\n"
            f"Blockers: "
            f"{', '.join(decision['blockers']) if decision['blockers'] else 'none'}"
        )

    return "\n\n".join(output)


def validate_chat(claim, question, draft):
    actual_sources = {
        record["id"]
        for record in core.CASES[claim]["records"]
    }

    cited = set(SOURCE_PATTERN.findall(draft))

    if cited - actual_sources:
        draft = (
            "An unverified AI response was withheld "
            "because it invented source identifiers."
        )

    if draft.startswith("Local AI unavailable"):
        draft = (
            "Local AI unavailable. The evidence verification "
            "engine remains available."
        )

    verified = evidence_summary(claim, question)

    return (
        draft.rstrip()
        + "\n\n--- Verified synthetic record review ---\n"
        + verified
        + "\n\nAI-generated prose is not independent evidence "
          "or a clinical determination."
    )


class App(care.App):

    def do_GET(self):
        if urlparse(self.path).path == "/":
            self.user()
            return self.respond(
                PAGE,
                mime="text/html; charset=utf-8"
            )

        return super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/message":
            return super().do_POST()

        owner = self.user()

        if self.headers.get("X-ClaimsLens-UI") != "1":
            return self.error(
                "Missing local UI header", 403
            )

        origin = self.headers.get("Origin", "")

        if origin and urlparse(origin).netloc != (
            self.headers.get("Host", "")
        ):
            return self.error(
                "Cross-origin request blocked", 403
            )

        try:
            length = int(
                self.headers.get("Content-Length", "-1")
            )

            if not 1 <= length <= 20000:
                return self.error(
                    "Invalid request size", 413
                )

            data = json.loads(
                self.rfile.read(length)
            )

            if not isinstance(data, dict):
                return self.error(
                    "Expected JSON object"
                )

            chat_id = str(data.get("chat", ""))
            question = str(data.get("text", "")).strip()

            if not 1 <= len(question) <= 3000:
                return self.error(
                    "Message length 1-3000"
                )

            with core.db() as database:
                session = database.execute(
                    """SELECT claim FROM chats
                       WHERE id=? AND owner=?""",
                    (chat_id, owner)
                ).fetchone()

            if (
                not session
                or session["claim"] not in core.CASES
            ):
                return self.error(
                    "Case-linked conversation not found", 404
                )

            # Reuse the existing integrated NCM agent.
            result = care.chat_agent(owner, data)

            answer = validate_chat(
                session["claim"],
                question,
                str(result["answer"])
            )

            # Update the saved assistant response, preserving history.
            with core.db() as database:
                previous = database.execute(
                    """SELECT id FROM turns
                       WHERE chat=? AND role='assistant'
                       ORDER BY id DESC LIMIT 1""",
                    (chat_id,)
                ).fetchone()

                if not previous:
                    raise ValueError(
                        "Assistant turn was not stored"
                    )

                database.execute(
                    "UPDATE turns SET body=? WHERE id=?",
                    (answer, previous["id"])
                )

            return self.respond({
                "answer": answer
            })

        except (ValueError, KeyError) as error:
            return self.error(error)

        except Exception as error:
            return self.error(
                type(error).__name__ + ": " + str(error),
                500
            )


def tests():
    assert len(core.CASES) == 240

    supported = 0
    rejected = 0

    for case in core.CASES.values():
        for obligation in case["orders"]:
            original = ORIGINAL_VERIFY(
                case, obligation
            )

            updated = verified_v2(
                case, obligation
            )

            # Confirm that existing verification results are preserved.
            assert (
                original["eligible_for_simulated_closure"]
                == updated["eligible_for_simulated_closure"]
            )

            support = set(
                updated["supporting_citations"]
            )

            rejection = set(
                updated["rejection_citations"]
            )

            assert not (support & rejection)

            known = {
                r["id"]
                for r in case["records"]
            }

            assert (support | rejection).issubset(known)

            if updated["eligible_for_simulated_closure"]:
                supported += 1
                assert updated["citations"] == list(support) or (
                    set(updated["citations"]) == support
                )
            else:
                rejected += 1
                assert updated["citations"] == []

    sample = evidence_summary(
        "CL-0001",
        "Is imaging completed?"
    )

    assert "Supporting completion sources" in sample
    assert "Inspection-only sources" in sample

    invalid = validate_chat(
        "CL-0001",
        "Is MRI completed?",
        "See CL-9999-SRC99"
    )

    assert "withheld" in invalid
    assert "CL-9999-SRC99" not in invalid

    assert 'id="prompt"' in PAGE
    assert "care-drawer" in PAGE

    print("\n=== CLAIMSLENS LIVE INTEGRATION ===")
    print("Original cases:", len(core.CASES))
    print("Supported obligations:", supported)
    print("Rejected obligations:", rejected)
    print("PASS: Citation types separated")
    print("PASS: No changes to verification decisions")
    print("PASS: Invented citations rejected")
    print("PASS: Chat-first interface retained")
    print("PASS: NCM Care workspace retained")
    print("Original source files not rewritten")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--test",
        action="store_true"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8526
    )

    args = parser.parse_args()

    if args.test:
        tests()

    else:
        with core.db():
            pass

        with care.database():
            pass

        server = ThreadingHTTPServer(
            ("127.0.0.1", args.port),
            App
        )

        print(
            "\nCLAIMSLENS — CHAT + NCM + CITATION V2"
        )
        print(
            f"http://127.0.0.1:{args.port}"
        )
        print(
            "Original research source files unchanged."
        )

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
