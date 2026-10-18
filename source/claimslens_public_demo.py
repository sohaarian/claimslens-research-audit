#!/usr/bin/env python3

"""
ClaimsLens Public Demonstration

Synthetic research data only.
No real patient information.
Public uploads and image processing disabled.
Original research files remain unchanged.
"""

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import urllib.request

from pathlib import Path
from collections import defaultdict, deque
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse

import claimslens_answer_evidence_v9 as existing
import claimslens_experience_review_v5 as review
import claimslens_research_fix_v3 as research

core = existing.core
care = existing.care


# ============================================================
# PUBLISH AGGREGATE RESEARCH RESULTS ONLY
# ============================================================

METRICS_FILE = Path(__file__).with_name(
    "public_ai_metrics.json"
)

if METRICS_FILE.is_file():

    saved = json.loads(
        METRICS_FILE.read_text()
    )

    def public_study_results():

        positive = 4
        negative = 60

        methods = []

        for key, name in research.NAMES.items():

            m = saved[key]

            methods.append({
                "key": key,
                "name": name,
                "completed": m["completed"],
                "accuracy": m["accuracy"],
                "ci": m.get("accuracy_wilson95"),
                "unsafe": m["unsafe_accepted"],
                "missed": m["missed_fixture_completions"],
                "supported": (
                    positive
                    - m["missed_fixture_completions"]
                ),
                "specificity": (
                    negative
                    - m["unsafe_accepted"]
                ) / negative,
                "sensitivity": (
                    positive
                    - m["missed_fixture_completions"]
                ) / positive,
                "errors": m.get("errors", 0),
            })

        return {
            "available": True,
            "run": "20261014T052534Z_92744",
            "n": 64,
            "positive": positive,
            "negative": negative,
            "methods": methods,
            "limitations": research.LIMITS,
            "synthetic_only": True,
        }

    research.study_results = public_study_results


# ============================================================
# SECURITY CONFIGURATION
# ============================================================

HOST = os.getenv(
    "RENDER_EXTERNAL_HOSTNAME", ""
)

SECRET_TEXT = os.getenv(
    "CL_SESSION_SECRET", ""
)

if os.getenv("RENDER") == "true":

    if (
        len(SECRET_TEXT) < 40
        or os.getenv("CL_PUBLIC_ACK")
        != "synthetic-only"
    ):

        raise SystemExit(
            "SECURITY STOP: Cloud configuration "
            "is incomplete."
        )

SECRET = (
    SECRET_TEXT
    or secrets.token_hex(32)
).encode()

LOCK = threading.Lock()
BUCKETS = defaultdict(deque)


# ============================================================
# OPTIONAL PRIVATE CLOUD AI
#
# No localhost Ollama is exposed.
# Configure a separate HTTPS model endpoint
# through cloud environment variables.
# ============================================================

AI_URL = os.getenv(
    "CL_LLM_CHAT_URL", ""
)

AI_KEY = os.getenv(
    "CL_LLM_API_KEY", ""
)

AI_MODEL = os.getenv(
    "CL_LLM_MODEL", ""
)

if AI_URL and (
    urlparse(AI_URL).scheme != "https"
    or not AI_KEY
    or not AI_MODEL
):

    raise SystemExit(
        "SECURITY STOP: Model requires HTTPS, "
        "an API key, and a configured model."
    )


def cloud_model(
    messages,
    image=None,
    model=None
):

    if image is not None:

        raise RuntimeError(
            "Public image AI is disabled."
        )

    if not AI_URL:

        raise RuntimeError(
            "Public demo uses source-review mode. "
            "Cloud AI is not configured."
        )

    payload = json.dumps({
        "model": AI_MODEL,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 450
    }).encode()

    if len(payload) > 18000:

        raise RuntimeError(
            "AI context budget exceeded."
        )

    request = urllib.request.Request(
        AI_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + AI_KEY
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=28
    ) as response:

        result = json.load(response)

    return str(
        result["choices"][0]["message"]["content"]
    )[:4500]


core.ollama = cloud_model


# ============================================================
# DISABLE UNSAFE PUBLIC ROUTES
# ============================================================

BLOCKED_GET = {
    "/api/preview",
    "/api/studio/metrics",
    "/api/studio/report"
}

BLOCKED_POST = {
    "/api/upload",
    "/api/vision",
    "/api/draft",
    "/api/notes"
}

ALLOWED_POST = {
    "/api/newchat",
    "/api/message",
    "/api/studio/action",
    "/api/review/start",
    "/api/review/action"
}


# ============================================================
# PUBLIC DEMO NOTICE
# ============================================================

PUBLIC_NOTICE = """
<div role="note" style="
    position:fixed;
    left:12px;
    bottom:10px;
    z-index:490;
    max-width:390px;
    padding:9px 14px;
    background:#153c42;
    color:#e8fff5;
    border:1px solid #4b9c8c;
    border-radius:10px;
    font:12px system-ui;
    box-shadow:0 5px 25px #0004">

    Public synthetic demonstration.
    Uploads and clinical use are disabled.
    Saved work may reset.

</div>
"""

PUBLIC_PAGE = existing.PAGE.replace(
    "</body>",
    PUBLIC_NOTICE + "</body>",
    1
)


# ============================================================
# PUBLIC SERVER WITH SIGNED VISITOR SESSIONS
# ============================================================

class App(existing.App):

    def setup(self):

        super().setup()

        self.connection.settimeout(18)


    def user(self):

        if hasattr(
            self,
            "_public_owner"
        ):

            return self._public_owner

        cookies = SimpleCookie()

        try:

            cookies.load(
                self.headers.get(
                    "Cookie", ""
                )
            )

            stored = cookies.get(
                "cl_owner_onepaste"
            )

            if stored:

                identifier, signature = (
                    stored.value.split(".", 1)
                )

                expected = hmac.new(
                    SECRET,
                    identifier.encode(),
                    hashlib.sha256
                ).hexdigest()

                valid_id = (
                    len(identifier) == 48
                    and all(
                        character in "0123456789abcdef"
                        for character in identifier
                    )
                )

                if (
                    valid_id
                    and hmac.compare_digest(
                        expected,
                        signature
                    )
                ):

                    self._public_owner = identifier

                    return identifier

        except (ValueError, TypeError):

            pass

        self.fresh = secrets.token_hex(24)

        self._public_owner = self.fresh

        return self._public_owner


    def send_header(
        self,
        keyword,
        value
    ):

        if (
            keyword.lower() == "set-cookie"
            and value.startswith(
                "cl_owner_onepaste="
            )
        ):

            identifier = self.user()

            signature = hmac.new(
                SECRET,
                identifier.encode(),
                hashlib.sha256
            ).hexdigest()

            secure = (
                "; Secure"
                if HOST else ""
            )

            value = (
                "cl_owner_onepaste="
                + identifier
                + "."
                + signature
                + "; Path=/; HttpOnly; SameSite=Lax"
                + secure
            )

        super().send_header(
            keyword,
            value
        )

        if keyword.lower() == "content-type":

            super().send_header(
                "Referrer-Policy",
                "strict-origin-when-cross-origin"
            )

            super().send_header(
                "Permissions-Policy",
                "camera=(), microphone=(), geolocation=()"
            )

            if HOST:

                super().send_header(
                    "Strict-Transport-Security",
                    "max-age=31536000; includeSubDomains"
                )


    # ========================================================
    # REQUEST LIMITS
    # ========================================================

    def _admit(
        self,
        write=False
    ):

        host = self.headers.get(
            "Host", ""
        ).lower()

        if (
            HOST
            and host != HOST.lower()
        ):

            self.error(
                "Host not permitted",
                421
            )

            return False

        if write:

            origin = self.headers.get(
                "Origin", ""
            )

            if (
                HOST
                and origin != "https://" + HOST
            ):

                self.error(
                    "Same-origin HTTPS requests only",
                    403
                )

                return False

            if (
                self.headers.get(
                    "X-ClaimsLens-UI"
                ) != "1"
            ):

                self.error(
                    "UI request header required",
                    403
                )

                return False

            if self.headers.get(
                "Sec-Fetch-Site",
                "same-origin"
            ) not in (
                "same-origin",
                "none"
            ):

                self.error(
                    "Cross-site requests denied",
                    403
                )

                return False

        session = self.user()
        now = time.monotonic()

        limits = [
            (
                ("global", write),
                75 if write else 240
            ),
            (
                (session, write),
                14 if write else 100
            )
        ]

        with LOCK:

            for key, maximum in limits:

                queue = BUCKETS[key]

                while (
                    queue
                    and queue[0] < now - 60
                ):

                    queue.popleft()

                if len(queue) >= maximum:

                    self.error(
                        "Demo is busy. "
                        "Please retry in a minute.",
                        429
                    )

                    return False

            for key, _ in limits:

                BUCKETS[key].append(now)

            if len(BUCKETS) > 5000:

                for key in list(BUCKETS):

                    queue = BUCKETS[key]

                    while (
                        queue
                        and queue[0] < now - 60
                    ):

                        queue.popleft()

                    if not queue:

                        del BUCKETS[key]

        return True


    # ========================================================
    # SAFE PUBLIC GET ROUTES
    # ========================================================

    def do_GET(self):

        path = urlparse(
            self.path
        ).path

        if path == "/healthz":

            return self.respond({
                "ok": True,
                "synthetic_demo": True
            })

        if not self._admit():

            return

        if path == "/":

            return self.respond(
                PUBLIC_PAGE,
                mime="text/html; charset=utf-8"
            )

        if path in BLOCKED_GET:

            return self.error(
                "Feature disabled in public demo",
                403
            )

        if path == "/api/uploads":

            return self.respond({
                "files": []
            })

        if path == "/api/assistant/health":

            return self.respond({
                "ready": bool(AI_URL),
                "configured_model": (
                    AI_MODEL or "source-only"
                ),
                "public_mode": True
            })

        return super().do_GET()


    # ========================================================
    # SAFE PUBLIC POST ROUTES
    # ========================================================

    def do_POST(self):

        path = urlparse(
            self.path
        ).path

        if (
            path in BLOCKED_POST
            or path not in ALLOWED_POST
        ):

            return self.error(
                "Action unavailable "
                "in the public demo",
                403
            )

        try:

            size = int(
                self.headers.get(
                    "Content-Length",
                    "-1"
                )
            )

        except ValueError:

            return self.error(
                "Invalid content length",
                400
            )

        if not 1 <= size <= 12000:

            return self.error(
                "Request exceeds demo limit",
                413
            )

        if not self._admit(
            write=True
        ):

            return

        return super().do_POST()


# ============================================================
# CLOUD STARTUP
# ============================================================

def main():

    port = int(
        os.getenv(
            "PORT",
            "8539"
        )
    )

    core.db().close()
    care.database().close()
    review.db().close()

    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        App
    )

    print(
        "ClaimsLens public synthetic demo "
        f"listening on port {port}",
        flush=True
    )

    print(
        "Uploads disabled. "
        "Visitor sessions enabled. "
        "Local Ollama disabled.",
        flush=True
    )

    server.serve_forever()


if __name__ == "__main__":

    main()
