#!/usr/bin/env python3
"""
CLAIMSLENS | CLINICAL INTELLIGENCE

One chat-first synthetic nurse case management product.

Reuses:
- Original 240-case ClaimsLens engine
- Original conversations, records, uploads and reports
- Existing evidence verifier and citation adapter
- Existing NCM risk, authorization, care and SOAP workflows
- Existing formatted research report exports

Runs on localhost only.
Never use with real patient information.
Does not edit previous application source or frozen research.
"""

import argparse
import json
import re
import tempfile
import threading
import urllib.error
import urllib.request

from collections import Counter
from contextlib import contextmanager
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import claimslens_research_fix_v3 as existing

studio = existing.studio
core = studio.core
care = studio.care


# ============================================================
# MARKET-STYLE DESIGN SYSTEM
# ============================================================

CSS = r'''
<style>

:root {
  --night: #101d2b;
  --navy: #183047;
  --teal: #117a74;
  --soft-teal: #e9f7f3;
  --line: #dbe4e8;
  --fog: #f3f6f8;
  --text: #192c3b;
  --muted: #668095;
}

body {
  background: #f3f6f8 !important;
  color: var(--text) !important;
  font-family:
    Inter, ui-sans-serif, system-ui,
    -apple-system, sans-serif !important;
}

.layout {
  grid-template-columns: 285px minmax(0,1fr) !important;
}

aside.sidebar {
  background: var(--night) !important;
  color: #dce9ed !important;
  border-right: 0 !important;
  padding: 24px 17px !important;
  gap: 13px !important;
}

.sidebar .logo {
  color: white !important;
  font-size: 23px !important;
  letter-spacing: -.9px !important;
}

.sidebar .logo span {
  background: linear-gradient(
    135deg,#17aaa0,#187b90
  ) !important;
  border-radius: 11px !important;
}

.sidebar .label,
.sidebar .small {
  color: #8faabc !important;
}

.sidebar input,
.sidebar select {
  background: #20364a !important;
  color: #f7fffd !important;
  border: 1px solid #344c5d !important;
  min-height: 43px !important;
}

.sidebar button {
  color: #e1ebef !important;
  border: 1px solid transparent !important;
  border-radius: 11px !important;
  padding: 10px !important;
}

.sidebar button:hover {
  background: #20374b !important;
}

.sidebar button#cl-browse {
  background: #24493f !important;
  color: #e7fff2 !important;
  border: 1px solid #2e7464 !important;
}

main {
  background:
    radial-gradient(
      circle at 50% 0%,
      #f3faf7 0%,
      #f8fafb 55%,
      #f8fafb 100%
    ) !important;
}

.top {
  height: 74px !important;
  padding: 0 30px !important;
  background: white !important;
  border-bottom: 1px solid #e5ebee !important;
}

.top strong {
  color: #152a3a !important;
  font-size: 17px !important;
  font-weight: 750 !important;
}

.top button {
  border-radius: 9px !important;
  font-weight: 650 !important;
}

#clp-launch {
  background: #152e43 !important;
  color: white !important;
  border: 0 !important;
  font-weight: 760 !important;
  padding: 10px 14px !important;
}

#clp-strip {
  margin: 0;
  padding: 13px 30px;
  background: white;
  border-bottom: 1px solid #e5edf0;
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 84px;
}

.clp-worker {
  font-size: 14px;
  font-weight: 800;
  color: #18364a;
}

.clp-details {
  color: #6b8290;
  font-size: 11px;
  margin-top: 3px;
}

.clp-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #1b9d7a;
  box-shadow: 0 0 0 4px #e2f6ed;
  flex: none;
}

.clp-pill {
  display: inline-flex;
  padding: 6px 10px;
  border-radius: 9px;
  background: #eaf6ef;
  color: #18684c;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}

.clp-pill-warn {
  background: #fff3dc;
  color: #906332;
}

.clp-spacer {
  flex: 1;
}

.clp-stripbtn {
  background: white;
  border: 1px solid #dce5e9;
  color: #345268;
  border-radius: 8px;
  padding: 8px 10px;
  font-weight: 650;
  font-size: 11px;
}

.messages {
  max-width: 940px !important;
  padding: 32px 28px !important;
}

.message .bubble {
  font-size: 14px !important;
  line-height: 1.75 !important;
}

.message.user .bubble {
  background: #e8eff1 !important;
  color: #1c3444 !important;
  border-radius: 17px !important;
}

.avatar {
  background: #deeee9 !important;
  color: #127466 !important;
  border-radius: 11px !important;
}

.composerouter {
  background: transparent !important;
  padding-bottom: 24px !important;
}

.composer {
  background: white !important;
  border: 1px solid #d7e4e6 !important;
  border-radius: 19px !important;
  box-shadow: 0 14px 30px #162c3310 !important;
  max-width: 890px !important;
}

.composer textarea {
  font-size: 14px;
  min-height: 56px !important;
}

.composer .send {
  background: #177e77 !important;
  color: white !important;
}

#clp-shortcuts {
  display: flex;
  max-width: 890px;
  margin: 0 auto 11px;
  gap: 7px;
  flex-wrap: wrap;
}

#clp-shortcuts button {
  border: 1px solid #d9e6e8;
  border-radius: 100px;
  background: white;
  color: #32576a;
  padding: 8px 13px;
  font-size: 11px;
  font-weight: 650;
}

#cl-panel {
  background: #f5f8fa !important;
  width: min(1120px,100vw) !important;
}

#clp-mask {
  position: fixed;
  inset: 0;
  background: #091a27b9;
  z-index: 88;
  display: none;
  backdrop-filter: blur(5px);
}

#clp-mask.show {
  display: block;
}

#clp-console {
  position: fixed;
  inset: 4vh 4vw;
  z-index: 89;
  background: #f6f9fa;
  border-radius: 19px;
  display: none;
  overflow: hidden;
  box-shadow: 0 25px 85px #06151f52;
  flex-direction: column;
  border: 1px solid #aec0c7;
}

#clp-console.show {
  display: flex;
}

.clp-header {
  padding: 20px 28px;
  background: linear-gradient(
    105deg,#132b3d,#173c4c 80%,#1a6258
  );
  color: white;
  display: flex;
  gap: 20px;
  align-items: center;
  flex-wrap: wrap;
}

.clp-header h2 {
  font-weight: 780;
  font-size: 25px;
  margin: 4px 0;
  letter-spacing: -.8px;
  color: white;
}

.clp-kicker {
  font-size: 11px;
  letter-spacing: .13em;
  text-transform: uppercase;
  color: #b1d9d2;
  font-weight: 700;
}

.clp-header small {
  color: #c2d5d9;
  font-size: 11px;
}

.clp-x {
  margin-left: auto;
  background: #ffffff20;
  border: 1px solid #ffffff54;
  color: white;
  border-radius: 10px;
  padding: 10px 16px;
}

.clp-tabs {
  display: flex;
  background: white;
  gap: 4px;
  padding: 12px 22px;
  border-bottom: 1px solid #e1e9ed;
  overflow-x: auto;
}

.clp-tabs button {
  border: 0;
  background: transparent;
  padding: 10px 17px;
  border-radius: 8px;
  color: #557084;
  font-size: 12px;
  font-weight: 740;
  white-space: nowrap;
}

.clp-tabs button.active {
  background: #e8f5f0;
  color: #116b5a;
}

.clp-content {
  padding: 22px 27px;
  overflow: auto;
  flex: 1;
}

.clp-grid {
  display: grid;
  grid-template-columns: repeat(12,minmax(0,1fr));
  gap: 14px;
}

.clp-stat {
  grid-column: span 3;
  background: white;
  padding: 21px;
  border-radius: 14px;
  border: 1px solid #dfe8ec;
  min-width: 0;
}

.clp-stat strong {
  display: block;
  font-size: 28px;
  letter-spacing: -1px;
  color: #15374b;
  margin: 8px 0 3px;
}

.clp-label {
  font-size: 11px;
  color: #668291;
  font-weight: 720;
}

.clp-card {
  background: white;
  border: 1px solid #dce6e9;
  border-radius: 14px;
  padding: 20px;
  grid-column: span 6;
  min-width: 0;
  box-shadow: 0 2px 8px #122f3905;
}

.clp-card.wide {
  grid-column: span 12;
}

.clp-card h3 {
  color: #1a3648;
  margin: 0 0 14px;
  font-size: 15px;
}

.clp-hint {
  color: #718998;
  font-size: 12px;
  margin-top: 12px;
  line-height: 1.65;
}

.clp-item {
  padding: 11px 0;
  border-bottom: 1px solid #e9eff0;
  font-size: 12px;
  display: flex;
  gap: 10px;
}

.clp-item b {
  color: #28465a;
}

.clp-item span {
  color: #627b89;
  line-height: 1.55;
}

.clp-source {
  font-size: 11px;
  font-family: ui-monospace,monospace;
  color: #16756b;
}

.clp-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.clp-buttons button,
.clp-btn {
  border: 1px solid #d4e3e4;
  background: #edf7f3;
  color: #185f54;
  border-radius: 9px;
  padding: 10px 12px;
  font-size: 12px;
  font-weight: 750;
}

.clp-buttons button.primary,
.clp-btn.primary {
  background: #17756c;
  color: white;
  border-color: #17756c;
}

.clp-alert {
  background: #fff8e9;
  border: 1px solid #f1dfaf;
  padding: 13px 15px;
  border-radius: 10px;
  color: #82622c;
  font-size: 12px;
  line-height: 1.65;
  margin: 12px 0;
}

.clp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.clp-table th,
.clp-table td {
  padding: 10px;
  border-bottom: 1px solid #e1e9eb;
  text-align: left;
  vertical-align: top;
}

.clp-table th {
  background: #f1f6f7;
  color: #526d7c;
  font-size: 11px;
}

.clp-select {
  width: 100%;
  margin: 5px 0 12px;
  padding: 9px;
  border: 1px solid #dae5e9;
  border-radius: 9px;
  background: white;
}

.clp-mono {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: #f5f8fa;
  border-radius: 10px;
  padding: 13px;
  font: 11px/1.6 ui-monospace,monospace;
  max-height: 320px;
  overflow: auto;
}

#clp-notice {
  position: fixed;
  right: 32px;
  bottom: 24px;
  z-index: 95;
  display: none;
  background: #17394d;
  color: white;
  padding: 14px 20px;
  border-radius: 11px;
  box-shadow: 0 10px 30px #0002;
  font-size: 12px;
}

@media(max-width:950px) {
  .clp-stat { grid-column: span 6; }
  .clp-card { grid-column: span 12; }
}

@media(max-width:700px) {
  .layout { display: block !important; }
  .sidebar { display: none !important; }
  #clp-console { inset: 0; border-radius: 0; }
  .clp-content { padding: 12px; }
  .clp-stat { grid-column: span 6; padding: 13px; }
  .clp-header { padding: 14px; }
  .clp-header h2 { font-size: 20px; }
}

</style>
'''


# ============================================================
# CLINICAL COMMAND CENTER
# ============================================================

UI = r'''
<div id="clp-mask"></div>

<section
  id="clp-console"
  role="dialog"
  aria-modal="true"
  aria-label="Clinical operations command center">

  <header class="clp-header">
    <div>
      <div class="clp-kicker">
        CLAIMSLENS / CLINICAL INTELLIGENCE
      </div>

      <h2>Care operations command center</h2>

      <small id="clp-case-title">
        Evidence-based decisions · Human in control
      </small>
    </div>

    <button class="clp-x" id="clp-close">
      Close ×
    </button>
  </header>

  <nav id="clp-tabs" class="clp-tabs"></nav>

  <div id="clp-content" class="clp-content"></div>
</section>

<div id="clp-notice" role="status"></div>

<script>
(() => {
  "use strict";

  const $ = id => document.getElementById(id);

  const esc = value => String(value ?? "").replace(
    /[&<>"']/g,
    char => ({
      "&":"&amp;",
      "<":"&lt;",
      ">":"&gt;",
      '"':"&quot;",
      "'":"&#39;"
    }[char])
  );

  const TABS = [
    "Overview",
    "Case obligations",
    "Nurse workflow",
    "Clinical evidence",
    "Research & QA"
  ];

  const state = {
    tab: "Overview",
    claim: null,
    data: null,
    busy: false
  };

  async function get(url) {
    const response = await fetch(url);

    const data = await response.json();

    if (!response.ok) {
      throw Error(data.error || "Request failed");
    }

    return data;
  }

  async function post(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-ClaimsLens-UI": "1"
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok) {
      throw Error(data.error || "Request failed");
    }

    return data;
  }

  function notify(text) {
    const box = $("clp-notice");
    box.textContent = text;
    box.style.display = "block";

    clearTimeout(notify.timeout);

    notify.timeout = setTimeout(
      () => box.style.display = "none",
      3500
    );
  }

  function currentCase() {
    return $("claim")?.value || "CL-0001";
  }

  const tag = (text, good=true) =>
    `<span class="clp-pill ${
      good ? "" : "clp-pill-warn"
    }">${esc(text)}</span>`;

  const item = (title, description, source="") =>
    `<div class="clp-item">
      <div style="flex:1">
        <b>${esc(title)}</b>

        <div>
          <span>${esc(description)}</span>
        </div>

        ${
          source
          ? `<div class="clp-source">${esc(source)}</div>`
          : ""
        }
      </div>
    </div>`;

  const card = (title, contents, wide=false) =>
    `<section class="clp-card ${wide ? "wide" : ""}">
      <h3>${esc(title)}</h3>
      ${contents}
    </section>`;

  const button = (title, action, primary=false) =>
    `<button
      data-clp-action="${esc(action)}"
      class="${primary ? "primary" : ""}">
      ${esc(title)}
    </button>`;

  const statistic = (label, value, description) =>
    `<div class="clp-stat">
      <div class="clp-label">${esc(label)}</div>
      <strong>${esc(value)}</strong>
      <div class="clp-hint">${esc(description)}</div>
    </div>`;

  function show() {
    $("clp-mask").classList.add("show");
    $("clp-console").classList.add("show");

    load().catch(
      error => notify(error.message)
    );
  }

  function hide() {
    $("clp-mask").classList.remove("show");
    $("clp-console").classList.remove("show");
  }

  async function load() {
    state.claim = currentCase();

    state.data = await get(
      "/api/clp/brief?claim="
      + encodeURIComponent(state.claim)
    );

    $("clp-case-title").textContent =
      state.claim
      + " · "
      + state.data.patient.worker
      + " · "
      + state.data.patient.title;

    render();
    renderStrip();
  }

  async function action(name, payload={}) {
    if (state.busy) return;

    state.busy = true;

    try {
      const response = await post(
        "/api/studio/action",
        {
          claim: state.claim,
          action: name,
          ...payload
        }
      );

      notify("Saved: " + name.replaceAll("_"," "));

      await load();
      return response;

    } catch (error) {
      notify("Action failed: " + error.message);

    } finally {
      state.busy = false;
    }
  }

  function renderStrip() {
    const data = state.data;

    if (!data) return;

    let strip = $("clp-strip");

    if (!strip) {
      strip = document.createElement("div");
      strip.id = "clp-strip";

      document.querySelector("main .top")?.after(strip);
    }

    strip.innerHTML = `
      <span class="clp-dot"></span>

      <div>
        <div class="clp-worker">
          ${esc(data.patient.worker)}
          <span class="clp-details">
            ${esc(data.patient.title)}
          </span>
        </div>

        <div class="clp-details">
          ${esc(data.patient.doi)}
          · ${esc(data.patient.doctor)}
          · Case ${esc(state.claim)}
        </div>
      </div>

      <span class="clp-spacer"></span>

      ${tag(
        data.counts.open+" evidence gaps",
        data.counts.open===0
      )}

      ${tag(
        data.counts.signed+" supported",
        true
      )}

      <button
        class="clp-stripbtn"
        id="clp-strip-open">
        Open clinical review ↗
      </button>
    `;

    $("clp-strip-open").onclick = show;
  }

  function render() {
    const data = state.data;
    if (!data) return;

    const nurse = data.ncm;
    const decisions = data.decisions;

    const open = decisions.filter(
      x => !x.eligible_for_simulated_closure
    );

    const supported = decisions.filter(
      x => x.eligible_for_simulated_closure
    );

    $("clp-tabs").innerHTML = TABS.map(
      name => `
        <button
          data-clp-tab="${esc(name)}"
          class="${state.tab===name ? "active" : ""}">
          ${esc(name)}
        </button>`
    ).join("");

    document.querySelectorAll("[data-clp-tab]").forEach(
      element => element.onclick = () => {
        state.tab = element.dataset.clpTab;
        render();
      }
    );

    let html = "";

    // ========================================================
    // OVERVIEW
    // ========================================================

    if (state.tab === "Overview") {
      html = `<div class="clp-grid">`;

      html += statistic(
        "Evidence supported",
        supported.length+" / 5",
        "Qualified synthetic source matches"
      );

      html += statistic(
        "Attention required",
        open.length,
        "Unverified service obligations"
      );

      html += statistic(
        "Follow-up tasks",
        nurse.tasks.length,
        "Persistent simulated worklist"
      );

      html += statistic(
        "Caseload",
        data.catalog_size,
        "Full synthetic claim library"
      );

      html += card(
        "Medical record intelligence",
        `<p class="clp-hint">
          A longitudinal timeline grounded in the
          source record, not an AI-generated diagnosis.
          Completion requires patient, order, authority,
          date, and attestation checks.
        </p>`

        + (
          open.map(x => item(
            x.label,
            x.blockers.join(", ") || "Matching source missing",
            (
              x.rejection_citations || []
            ).join(", ") || "No qualified completion evidence"
          )).join("")

          || item(
            "All tracked obligations supported",
            "Review evidence before administrative action."
          )
        )
      );

      html += card(
        "Nurse case management tools",

        `<div class="clp-buttons">
          ${button("Generate nurse worklist","worklist",true)}
          ${button("Draft source-linked SOAP","soap")}
          ${button("Review authorization packet","auth")}
          ${button("Open clinical workspace","studio")}
        </div>

        <p class="clp-hint">
          All actions remain attached to ${esc(state.claim)}.
          The AI cannot authorize care, diagnose injury,
          or close unsupported obligations.
        </p>

        <div class="clp-alert">
          Research demonstration. Fictional records and
          policies only. No protected health information
          or autonomous medical decisions.
        </div>`
      );

      html += card(
        "Care team",

        item(
          "Treating physician",
          data.patient.doctor
        )

        + item(
          "Claims adjuster",
          data.patient.adjuster
        )

        + item(
          "Illustrative diagnosis code",
          data.patient.icd
        )
      );

      html += card(
        "Demonstration workflow",

        item(
          "1. Review",
          "Inspect full record and appointment chronology"
        )

        + item(
          "2. Resolve gaps",
          "Track missing final notes and utilization decisions"
        )

        + item(
          "3. Prepare",
          "Build a worklist, authorization packet and SOAP draft"
        )

        + item(
          "4. Verify",
          "Export documentation and review limitations"
        )
      );

      html += `</div>`;
    }

    // ========================================================
    // CASE OBLIGATIONS
    // ========================================================

    if (state.tab === "Case obligations") {
      const contents = decisions.map(
        x => `
          <div class="clp-item">

            <div style="flex:1">
              <b>${esc(x.label)}</b>

              ${tag(
                x.eligible_for_simulated_closure
                  ? "REPORT DOCUMENTED"
                  : "NEEDS REVIEW",
                x.eligible_for_simulated_closure
              )}

              <div class="clp-hint">
                Supporting proof:
                ${esc(
                  (x.supporting_citations || []).join(", ")
                  || "None"
                )}

                <p>
                  Inspected but not proof:
                  ${esc(
                    (x.rejection_citations || []).join(", ")
                    || "None"
                  )}
                </p>

                Blockers:
                ${esc(x.blockers.join(", ") || "None")}
              </div>

              <details>
                <summary>
                  Review individual source checks
                </summary>

                <pre class="clp-mono">${
                  esc(JSON.stringify(x.traces,null,2))
                }</pre>
              </details>
            </div>
          </div>
        `
      ).join("");

      html = `<div class="clp-grid">`;

      html += card(
        "Clinical evidence ledger",

        `<div class="clp-alert">
          Inspection-only records must never be presented
          as evidence supporting medical completion.
        </div>`

        + contents,
        true
      );

      html += "</div>";
    }

    // ========================================================
    // NURSE WORKFLOW
    // ========================================================

    if (state.tab === "Nurse workflow") {
      const auth = nurse.authorization;

      html = `<div class="clp-grid">`;

      html += card(
        "Worklist and follow-up",

        `<div class="clp-buttons">
          ${button("Build worklist","worklist",true)}
          ${button("Generate SOAP","soap")}
        </div>`

        + (
          nurse.tasks.map(
            task => `
              <div class="clp-item">
                <div style="flex:1">
                  <b>${esc(task.title)}</b>

                  <select
                    data-clp-task="${task.id}"
                    class="clp-select">

                    ${
                      [
                        "OPEN",
                        "IN_PROGRESS",
                        "BLOCKED",
                        "DONE"
                      ].map(
                        status => `
                          <option ${
                            status===task.status
                              ? "selected"
                              : ""
                          }>
                            ${status}
                          </option>
                        `
                      ).join("")
                    }

                  </select>
                </div>
              </div>
            `
          ).join("")

          || `<p class="clp-hint">
            No tasks accepted yet.
            Use Build worklist to generate source-linked
            follow-up recommendations.
          </p>`
        )
      );

      html += card(
        "Prior authorization readiness",

        tag(
          auth.packet_ready_demo
            ? "DOCUMENTATION COLLECTED"
            : "DOCUMENTATION INCOMPLETE",
          auth.packet_ready_demo
        )

        + `<p class="clp-hint">
          Fictional payer requirements.
          Documentation readiness does not establish
          actual insurance approval.
        </p>`

        + (
          (auth.missing || []).map(
            requirement => item(
              requirement,
              "Required source documentation missing"
            )
          ).join("")

          || `<p class="clp-hint">
            All listed fictional requirements recorded.
          </p>`
        )

        + `<div class="clp-buttons">
          ${button(
            "Open authorization workspace",
            "auth",
            true
          )}
        </div>`
      );

      html += card(
        "Discharge barriers and social needs",

        (
          nurse.care.map(
            need => item(
              need.need,
              need.status,
              "Fictional services only"
            )
          ).join("")

          || `<p class="clp-hint">
            No barriers recorded.
            An empty worklist does not establish
            an absence of patient needs.
          </p>`
        )

        + `<form id="clp-need">
          <label class="clp-hint">
            Track a new care coordination barrier
          </label>

          <input
            class="clp-select"
            name="need"
            maxlength="100"
            required
            placeholder="e.g. transportation">

          <button class="clp-btn primary">
            Save barrier
          </button>
        </form>`
      );

      html += card(
        "Clinical documentation",

        item(
          nurse.notes.length+" SOAP notes",
          "Draft or simulated reviewed documentation"
        )

        + `<div class="clp-buttons">
          ${button("Draft SOAP note","soap",true)}
          ${button("Reviewer workspace","soapview")}
        </div>

        <p class="clp-hint">
          Source-based drafts require human review
          and correction. A simulated review is
          not a legal clinical signature.
        </p>`
      );

      html += "</div>";
    }

    // ========================================================
    // CLINICAL RECORD
    // ========================================================

    if (state.tab === "Clinical evidence") {
      const latest = data.timeline.slice(-18).reverse();

      html = `<div class="clp-grid">`;

      html += card(
        "Longitudinal clinical timeline",

        `<p class="clp-hint">
          Orders, completed medical services and
          scheduling correspondence remain separate.
        </p>`

        + latest.map(
          event => item(
            event.date+" · "+event.kind,
            event.title,
            event.source
          )
        ).join(""),
        true
      );

      html += card(
        "Detailed medical record workspace",

        `<p class="clp-hint">
          The complete Inbox, appointment records,
          imaging previews, uploaded documents, and
          editable reports remain available in
          the original workspace.
        </p>

        <div class="clp-buttons">
          ${button("Open full records","original",true)}
          ${button("Open Clinical Studio","studio")}
        </div>`,
        true
      );

      html += "</div>";
    }

    // ========================================================
    // RESEARCH AND PRODUCT QUALITY
    // ========================================================

    if (state.tab === "Research & QA") {
      const study = data.research;
      const methods = study.available ? study.methods : [];

      html = `<div class="clp-grid">`;

      html += card(
        "Evidence-gated AI evaluation",

        `<p class="clp-hint">
          Saved synthetic experiment.
          These are not clinical performance estimates.
        </p>`

        + (
          study.available

          ? `<table class="clp-table">
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Accuracy</th>
                  <th>Valid recognized</th>
                  <th>Unsafe accepted</th>
                </tr>
              </thead>

              <tbody>
                ${
                  methods.map(
                    method => `
                      <tr>
                        <td>${esc(method.name)}</td>
                        <td>${
                          (method.accuracy*100).toFixed(2)
                        }%</td>
                        <td>${
                          esc(method.supported)
                        }/${esc(study.positive)}</td>
                        <td>${
                          esc(method.unsafe)
                        }/${esc(study.negative)}</td>
                      </tr>
                    `
                  ).join("")
                }
              </tbody>
            </table>

            <div class="clp-alert">
              The email-only method achieved high
              accuracy while recognizing none of
              the true completions in the sample.

              Only ${esc(study.positive)} of
              ${esc(study.n)} cases were positive.

              Overall accuracy is not enough
              to establish real-world clinical safety.
            </div>`

          : `<p class="clp-hint">
              No saved AI metrics were found.
            </p>`
        ),
        true
      );

      html += card(
        "Historical module integrity",

        `<p class="clp-hint">
          Existing research files are preserved.
          File presence is not proof of exact
          runtime integration.
        </p>`

        + Object.entries(data.modules).map(
          ([name,value]) => item(name,value)
        ).join("")
      );

      html += card(
        "Research and technical reports",

        `<p class="clp-hint">
          This launcher can run Python regression
          tests, source integrity checks,
          HTTP workflows, and document exports.
        </p>

        <div class="clp-buttons">
          ${button("View formatted report","research",true)}
          ${button("Research PDF","pdf")}
          ${button("Research Word","word")}
        </div>`
      );

      html += "</div>";
    }

    $("clp-content").innerHTML = html;

    document.querySelectorAll(
      "[data-clp-action]"
    ).forEach(
      element => element.onclick = () =>
        command(element.dataset.clpAction)
    );

    document.querySelectorAll(
      "[data-clp-task]"
    ).forEach(
      element => element.onchange = () =>
        action("update_task", {
          id: element.dataset.clpTask,
          status: element.value
        })
    );

    const needForm = $("clp-need");

    if (needForm) {
      needForm.onsubmit = event => {
        event.preventDefault();

        action("add_need", {
          need: new FormData(
            needForm
          ).get("need")
        });
      };
    }
  }

  // ==========================================================
  // CONNECT COMMAND CENTER TO ORIGINAL PRODUCT
  // ==========================================================

  function command(name) {
    if (name === "worklist") {
      return action("create_worklist");
    }

    if (name === "soap") {
      return action("create_soap");
    }

    if (["studio","auth","soapview"].includes(name)) {
      hide();

      const studioButton = [
        ...document.querySelectorAll(".top button")
      ].find(
        button => button.textContent.includes(
          "Clinical Studio"
        )
      );

      if (!studioButton) {
        notify("Clinical Studio button not available");
        return;
      }

      studioButton.click();

      if (name !== "studio") {
        const tab = name==="auth"
          ? "Authorization"
          : "SOAP";

        setTimeout(
          () => {
            document.querySelector(
              `[data-tab="${tab}"]`
            )?.click();
          },
          450
        );
      }

      return;
    }

    if (name === "original") {
      hide();
      document.querySelector("#open")?.click();
      return;
    }

    if (["research","pdf","word"].includes(name)) {
      const suffix = name==="research"
        ? "preview"
        : name;

      window.open(
        "/api/studio/research/"
        + suffix
        + "?claim="
        + encodeURIComponent(state.claim),
        "_blank",
        "noopener"
      );
    }
  }

  $("clp-mask").onclick = hide;
  $("clp-close").onclick = hide;

  document.addEventListener("keydown", event => {
    if (event.key === "Escape") {
      hide();
    }

    if (
      (event.metaKey || event.ctrlKey)
      && event.key.toLowerCase() === "k"
    ) {
      event.preventDefault();
      show();
    }
  });

  const launchButton = document.createElement("button");

  launchButton.id = "clp-launch";
  launchButton.textContent = "▦ Command center";
  launchButton.onclick = show;

  document.querySelector(".top .row")?.prepend(
    launchButton
  );

  const tagLine = document.createElement("div");

  tagLine.style.cssText = `
    font-size:10px;
    color:#a9c3cc;
    margin:-5px 0 8px;
    padding-left:50px;
    letter-spacing:.05em
  `;

  tagLine.textContent =
    "CLINICAL INTELLIGENCE · RESEARCH";

  document.querySelector(
    ".sidebar .logo"
  )?.after(tagLine);

  // Useful natural-language prompts.

  const quickActions = [
    [
      "Review open obligations",
      "Which obligations need verification?"
    ],
    [
      "Summarize with citations",
      "Summarize this case with sources"
    ],
    [
      "Prepare authorization",
      "Prepare authorization packet"
    ],
    [
      "Build worklist",
      "Build my nurse worklist"
    ],
    [
      "Draft SOAP",
      "Draft SOAP note"
    ]
  ];

  const shortcuts = document.createElement("div");
  shortcuts.id = "clp-shortcuts";

  for (const [label,prompt] of quickActions) {
    const button = document.createElement("button");

    button.textContent = label;

    button.onclick = () => {
      const input = $("prompt");
      input.value = prompt;
      input.focus();

      $("send")?.click();
    };

    shortcuts.append(button);
  }

  document.querySelector(
    ".composerouter"
  )?.prepend(shortcuts);

  $("claim")?.addEventListener(
    "change",
    () => setTimeout(
      () => load().catch(() => {}),
      220
    )
  );

  setTimeout(
    () => load().catch(
      error => console.warn(
        "Clinical header unavailable:",
        error
      )
    ),
    900
  );

})();
</script>
'''


PAGE = (
    existing.PAGE
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
# SERVER DATA AND HISTORICAL MODULE INVENTORY
# ============================================================

def module_integrity():
    names = [
        "claimslens_final.py",
        "claimslens_citation_protocol_v2.py",
        "assurancenet.py",
        "claimslens_ncm_prototype.py",
    ]

    folder = Path(__file__).resolve().parent

    statuses = {}

    for name in names:
        path = folder / name

        if not path.is_file():
            statuses[name] = "Not found in application folder"

        elif name == "claimslens_final.py":
            statuses[name] = (
                "Present — original product engine active"
            )

        else:
            statuses[name] = (
                "Present — historical module retained; "
                "exact direct integration not verified"
            )

    return statuses


def clinical_brief(owner, claim_id):
    if claim_id not in core.CASES:
        raise ValueError(
            "Unknown fictional claim"
        )

    data = studio.workspace(
        owner,
        claim_id
    )

    decisions = data["decisions"]

    return {
        "patient": {
            "worker": data["name"],
            "title": data["title"],
            "doi": data["doi"],
            "doctor": data["doctor"],
            "adjuster": data["adjuster"],
            "icd": data["icd"],
        },

        "decisions": decisions,

        "timeline": data["timeline"],

        "ncm": data["ncm"],

        "counts": {
            "open": sum(
                not x["eligible_for_simulated_closure"]
                for x in decisions
            ),

            "signed": sum(
                x["eligible_for_simulated_closure"]
                for x in decisions
            ),
        },

        "catalog_size": len(core.CASES),

        "research": existing.study_results(),

        "modules": module_integrity(),

        "synthetic_only": True,
    }


class App(existing.App):

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self.user()
            return self.respond(
                PAGE,
                mime="text/html; charset=utf-8"
            )

        if path == "/api/clp/brief":
            owner = self.user()

            claim = parse_qs(
                urlparse(self.path).query
            ).get("claim",[""])[0]

            try:
                return self.respond(
                    clinical_brief(owner,claim)
                )

            except (ValueError,KeyError) as error:
                return self.error(error,422)

        if path == "/api/clp/health":
            self.user()

            return self.respond({
                "ok": True,
                "original_cases": len(core.CASES),
                "synthetic_only": True,
                "modules": module_integrity()
            })

        return super().do_GET()


# ============================================================
# AUTOMATED SAFETY AND FUNCTIONAL TEST SUITE
# ============================================================

@contextmanager
def disposable_state():
    """
    All test writes go into temporary databases.
    Existing patient-demo conversations and research
    outputs are not modified by testing.
    """

    previous = (
        core.ROOT,
        core.DB,
        core.UPLOAD_DIR,
        care.EXT_DB,
    )

    with tempfile.TemporaryDirectory(
        prefix="claimslens_product_qa_"
    ) as directory:

        root = Path(directory)

        core.ROOT = root / "original"
        core.DB = core.ROOT / "data.sqlite3"
        core.UPLOAD_DIR = core.ROOT / "uploads"

        care.EXT_DB = root / "nurse.sqlite3"

        try:
            yield

        finally:
            (
                core.ROOT,
                core.DB,
                core.UPLOAD_DIR,
                care.EXT_DB,
            ) = previous


def test_evidence_engine():
    """
    Verify every synthetic claim and its five
    tracked care obligations.
    """

    assert len(core.CASES) == 240

    assert sum(
        len(c["emails"])
        for c in core.CASES.values()
    ) == 4800

    assert sum(
        len(c["appointments"])
        for c in core.CASES.values()
    ) == 1200

    assert sum(
        len(c["orders"])
        for c in core.CASES.values()
    ) == 1200

    totals = Counter()

    for claim_id, case in core.CASES.items():
        decisions = core.evidence(case)

        assert len(decisions) == 5

        known_sources = {
            record["id"]
            for record in case["records"]
        }

        for decision in decisions:
            proof = set(
                decision.get(
                    "supporting_citations", []
                )
            )

            rejected = set(
                decision.get(
                    "rejection_citations", []
                )
            )

            assert not (proof & rejected)

            assert (
                proof | rejected
            ).issubset(known_sources)

            if decision[
                "eligible_for_simulated_closure"
            ]:
                assert proof
                totals["supported"] += 1

            else:
                assert not proof
                totals["rejected"] += 1

        imaging = decisions[0]

        assert (
            imaging[
                "eligible_for_simulated_closure"
            ]
            == (case["scenario"]=="complete")
        ), claim_id

    assert totals["supported"] == 283
    assert totals["rejected"] == 917

    print(
        "PASS: 240 cases, 4,800 emails, "
        "1,200 appointments, 1,200 obligations"
    )

    print(
        "PASS: 283 supported and 917 rejected "
        "obligations with separate citations"
    )

    print(
        "PASS: No unsafe imaging closures "
        "across original scenario fixtures"
    )


def test_javascript():
    """
    Syntax check every integrated JavaScript block.
    Requires Node for this additional test.
    """

    import shutil
    import subprocess

    if not shutil.which("node"):
        print(
            "SKIP: Node.js not installed; "
            "manual JavaScript browser check needed"
        )
        return

    scripts = re.findall(
        r"<script\b[^>]*>(.*?)</script>",
        PAGE,
        flags=re.I | re.S,
    )

    with tempfile.TemporaryDirectory() as folder:
        for index, source in enumerate(scripts):
            path = Path(folder) / (
                "test_"+str(index)+".js"
            )

            path.write_text(source)

            result = subprocess.run(
                ["node","--check",str(path)],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0, result.stderr

    print(
        "PASS: All integrated browser scripts "
        "pass JavaScript syntax checks"
    )


def test_http_and_workflows():
    """
    Start a real disposable localhost HTTP server.

    Exercise:
    - All cases
    - Medical source verification
    - Saved AI conversation
    - Authorization, worklist and SOAP actions
    - Synthetic risk updates
    - Upload source authority safeguards
    - Case and research PDF/Word exports
    """

    with disposable_state():

        server = ThreadingHTTPServer(
            ("127.0.0.1",0),
            App,
        )

        thread = threading.Thread(
            target=server.serve_forever,
            daemon=True,
        )

        thread.start()

        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(
                CookieJar()
            )
        )

        base = (
            "http://127.0.0.1:"
            + str(server.server_port)
        )

        def get(endpoint):
            with opener.open(
                base+endpoint,
                timeout=15
            ) as response:
                return response.read()

        def post(endpoint,payload):
            request = urllib.request.Request(
                base+endpoint,
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type":"application/json",
                    "X-ClaimsLens-UI":"1",
                },
                method="POST"
            )

            with opener.open(
                request,
                timeout=25
            ) as response:
                return json.load(response)

        try:
            # Validate the actual rendered application.

            html = get("/").decode()

            assert 'id="prompt"' in html
            assert "clp-console" in html
            assert "cl-choose" in html

            # Confirm all 240 claims are retrievable.

            catalog = json.loads(
                get("/api/catalog")
            )["cases"]

            assert len(catalog)==240
            assert catalog[-1]["id"]=="CL-0240"

            assert json.loads(
                get("/api/clp/health")
            )["ok"]

            claim_id = "CL-0001"

            current = json.loads(
                get(
                    "/api/clp/brief?claim="
                    +claim_id
                )
            )

            assert current["catalog_size"]==240
            assert len(current["decisions"])==5

            last = json.loads(
                get(
                    "/api/clp/brief?claim=CL-0240"
                )
            )

            assert last["patient"]["worker"]

            print(
                "PASS: Actual HTTP application, "
                "case explorer and clinical API"
            )

            # Create a saved conversation.

            chat = post(
                "/api/newchat",
                {"claim":claim_id}
            )["id"]

            answer = post(
                "/api/message",
                {
                    "chat":chat,
                    "text":"Which obligations need verification?"
                }
            )["answer"]

            assert (
                "Supporting completion sources" in answer
                or "Supporting completion citations" in answer
            )

            assert "CL-0001-SRC" in answer

            conversation = json.loads(
                get("/api/chat?id="+chat)
            )

            assert len(conversation["turns"])==2
            assert conversation["turns"][-1]["body"]==answer

            print(
                "PASS: Saved source-grounded AI "
                "conversation and case citations"
            )

            # Exercise nurse workflow endpoints.

            post(
                "/api/studio/action",
                {
                    "claim":claim_id,
                    "action":"create_worklist"
                }
            )

            post(
                "/api/studio/action",
                {
                    "claim":claim_id,
                    "action":"add_need",
                    "need":"transportation"
                }
            )

            note = post(
                "/api/studio/action",
                {
                    "claim":claim_id,
                    "action":"create_soap"
                }
            )

            assert note["status"]=="DRAFT"

            updated = json.loads(
                get(
                    "/api/clp/brief?claim="+claim_id
                )
            )["ncm"]

            assert updated["tasks"]
            assert updated["care"]
            assert updated["notes"]
            assert updated["authorization"]["draft"]

            assert not updated[
                "authorization"
            ].get("payer_approval_verified",False)

            print(
                "PASS: Same-case worklist, "
                "discharge need, authorization and SOAP"
            )

            # Test actions initiated from natural language.

            commands = [
                ("Prepare authorization packet","FICTIONAL"),
                ("Draft SOAP note","SOAP"),
                ("Build my nurse worklist","follow-up tasks"),
            ]

            for prompt, expected in commands:
                result = post(
                    "/api/message",
                    {
                        "chat":chat,
                        "text":prompt
                    }
                )["answer"]

                assert expected.lower() in result.lower(), result

            history = json.loads(
                get("/api/chat?id="+chat)
            )["turns"]

            assert len(history)==8

            print(
                "PASS: Natural-language authorization, "
                "SOAP and worklist actions persisted in chat"
            )

            # Risk changes must not bypass source verification.

            before = json.loads(
                get(
                    "/api/check?claim="+claim_id
                )
            )["decisions"]

            features = updated["risk"]["features"]

            if "heart_rate" in features:
                post(
                    "/api/studio/action",
                    {
                        "claim":claim_id,
                        "action":"simulate_risk",
                        "feature":"heart_rate",
                        "value":110
                    }
                )

                revised = json.loads(
                    get(
                        "/api/clp/brief?claim="+claim_id
                    )
                )["ncm"]

                assert (
                    revised["risk"]["features"]["heart_rate"]
                    ==110
                )

            after = json.loads(
                get(
                    "/api/check?claim="+claim_id
                )
            )["decisions"]

            assert [
                x["eligible_for_simulated_closure"]
                for x in before
            ] == [
                x["eligible_for_simulated_closure"]
                for x in after
            ]

            print(
                "PASS: Risk simulation cannot change "
                "medical obligation closure"
            )

            # Upload a fictional unverified record.
            # It must NOT authorize medical completion.

            upload_request = urllib.request.Request(
                base
                +"/api/upload?claim="
                +claim_id
                +"&name=fictional_note.txt",

                data=(
                    b"Fictional record. "
                    b"This is not a signed final imaging report."
                ),

                headers={
                    "X-ClaimsLens-UI":"1",
                    "Content-Type":"text/plain"
                },

                method="POST"
            )

            with opener.open(
                upload_request,
                timeout=15
            ) as response:
                uploaded = json.load(response)

            assert uploaded["id"]

            files = json.loads(
                get(
                    "/api/uploads?claim="+claim_id
                )
            )["files"]

            assert any(
                x["id"]==uploaded["id"]
                for x in files
            )

            after_upload = json.loads(
                get(
                    "/api/check?claim="+claim_id
                )
            )["decisions"]

            assert [
                x["eligible_for_simulated_closure"]
                for x in after
            ] == [
                x["eligible_for_simulated_closure"]
                for x in after_upload
            ]

            print(
                "PASS: Unverified uploaded documents "
                "do not establish medical completion"
            )

            # Original case report exports.

            for format, magic in [
                ("pdf",b"%PDF"),
                ("docx",b"PK")
            ]:
                content = get(
                    "/api/export?claim="
                    +claim_id
                    +"&format="+format
                )

                assert content.startswith(magic)
                assert len(content)>3000

            # Formatted research exports.

            for format, magic in [
                ("preview",b"<!doctype html>"),
                ("pdf",b"%PDF"),
                ("word",b"PK")
            ]:
                content = get(
                    "/api/studio/research/"
                    +format
                    +"?claim="
                    +claim_id
                )

                assert content.startswith(magic)
                assert len(content)>3000

            print(
                "PASS: Original and research "
                "PDF/Word/HTML report exports"
            )

            # Negative-case source validation.

            rejected = json.loads(
                get(
                    "/api/check?claim=CL-0002"
                )
            )["decisions"][0]

            assert not rejected[
                "eligible_for_simulated_closure"
            ]

            assert not rejected[
                "supporting_citations"
            ]

            print(
                "PASS: Live negative-case "
                "evidence and citation safety"
            )

        finally:
            server.shutdown()
            server.server_close()

            thread.join(timeout=3)


def test_browser_optional():
    """
    Static browser integrity test.

    UI interaction can also be manually tested
    in Chrome after startup.
    """
    assert "clp-launch" in PAGE
    assert "clp-console" in PAGE
    assert "clp-strip" in PAGE
    assert "cl-browse" in PAGE

    print(
        "PASS: New command-center UI, "
        "case explorer and original chat markup"
    )

    print(
        "MANUAL CHECK: Open Chrome, switch cases, "
        "open Command center, create a task and "
        "SOAP draft, then inspect research exports."
    )


# ============================================================
# APPLICATION LAUNCHER
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="ClaimsLens Clinical Intelligence"
    )

    parser.add_argument(
        "--test",
        action="store_true"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8533
    )

    args = parser.parse_args()

    if args.test:
        test_evidence_engine()
        test_javascript()
        test_http_and_workflows()
        test_browser_optional()

        print(
            "\nCLAIMSLENS TECHNICAL TESTS PASSED"
        )

        print(
            "Ready for a manual clinical workflow demonstration."
        )

        print(
            "NOT independently clinically validated."
        )

        return

    assert 1024 <= args.port <= 65535

    with core.db():
        pass

    with care.database():
        pass

    server = ThreadingHTTPServer(
        ("127.0.0.1",args.port),
        App
    )

    print(
        "\nCLAIMSLENS | CLINICAL INTELLIGENCE"
    )

    print(
        f"http://127.0.0.1:{args.port}"
    )

    print(
        "240-case chat-first synthetic platform."
    )

    print(
        "Original application and research files retained."
    )

    print(
        "Press Control+C to stop the server."
    )

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        server.server_close()


if __name__=="__main__":
    main()
