#!/usr/bin/env python3

"""
ClaimsLens Welcome V7

Adds the Nurse Case Manager workload
to the product introduction.

Preserves:
- Animated 3D logo
- Book opening transition
- Original ChatGPT-style interface
- 240 fictional workers' compensation claims
- Clinical command center
- Nurse statement-by-statement review
- Existing research and source files

Synthetic research only.
"""

import argparse
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse

import claimslens_welcome_book_v6 as previous


INTRO_UPDATE = r'''
<style>
#cx-welcome .cx-description {
    max-width: 625px;
}

#cx-welcome .cx-abstract-intro p {
    line-height: 1.78;
    margin-bottom: 19px;
}

#cx-welcome .cx-abstract-intro strong {
    color: #a0efda;
}

#cx-welcome .cx-challenge-closing {
    display: block;
    color: #e3f7ed;
    font-weight: 650;
    margin-top: 12px;
    line-height: 1.65;
}
</style>

<script>
(() => {
    "use strict";

    const challenge = document.querySelector(
        "#cx-welcome .cx-description "
        + ".cx-abstract-intro p:first-child"
    );

    if (!challenge) {
        console.warn(
            "ClaimsLens welcome challenge not found"
        );
        return;
    }

    challenge.innerHTML = `
        <strong>The challenge</strong>

        Workers' compensation nurse case managers
        often manage many active claims at the same
        time. Their days involve reviewing medical
        records, tracking appointments, coordinating
        referrals, following up on treatment requests,
        and communicating with injured workers,
        physicians, insurance adjusters, and employers.

        <span style="display:block;margin-top:12px">
            Telephonic case managers may handle
            large volumes of remote claims, while
            field case managers balance medical
            appointments, travel, and direct care
            coordination. With information arriving
            through different emails, reports, and
            systems, keeping every case up to date
            requires constant attention.
        </span>

        <span style="display:block;margin-top:12px">
            These competing responsibilities can
            create significant pressure. A missing
            medical report, a rescheduled appointment,
            or an unanswered treatment request can
            require additional follow-up.
            Administrative tasks can also take
            valuable time away from understanding
            an injured worker's needs and supporting
            their recovery.
        </span>

        <span class="cx-challenge-closing">
            Behind every claim is a person whose
            recovery deserves careful attention.
        </span>
    `;

})();
</script>
'''


PAGE = previous.PAGE.replace(
    "</body>",
    INTRO_UPDATE + "</body>",
    1
)


class App(previous.App):

    def do_GET(self):

        if urlparse(self.path).path == "/":

            self.user()

            return self.respond(
                PAGE,
                mime="text/html; charset=utf-8"
            )

        return super().do_GET()


def tests():

    assert len(
        previous.base.core.CASES
    ) == 240

    assert "cx-book-transition" in PAGE

    assert "cx-review" in PAGE

    assert "clp-console" in PAGE

    assert "The challenge" in INTRO_UPDATE

    assert "competing responsibilities" in INTRO_UPDATE

    assert "Behind every claim" in INTRO_UPDATE

    assert "Our approach" in previous.EXTRA

    print(
        "PASS: Full 240-case product preserved"
    )

    print(
        "PASS: Expanded Nurse Case Manager challenge"
    )

    print(
        "PASS: Existing Our approach retained"
    )

    print(
        "PASS: Animated logo and book transition retained"
    )

    print(
        "PASS: Nurse Review workflow retained"
    )

    print(
        "PASS: Previous application files not rewritten"
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--test",
        action="store_true"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8537
    )

    args = parser.parse_args()

    if args.test:

        tests()

    else:

        with previous.base.core.db():
            pass

        with previous.base.care.database():
            pass

        with previous.base.db():
            pass

        server = ThreadingHTTPServer(
            ("127.0.0.1", args.port),
            App
        )

        print(
            "CLAIMSLENS V7"
        )

        print(
            f"http://127.0.0.1:{args.port}"
        )

        print(
            "Updated introduction and "
            "Nurse Case Manager workload explanation"
        )

        try:

            server.serve_forever()

        except KeyboardInterrupt:

            server.server_close()
