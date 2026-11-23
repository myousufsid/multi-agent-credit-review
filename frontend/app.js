/**
 * app.js — Stage 5: Credit Review Dashboard
 *
 * Fetches the full Supervisor Agent workflow result from the backend,
 * then renders each section of the dashboard from the returned JSON.
 *
 * All displayed values come directly from the API response.
 * No financial metrics are hardcoded here.
 */

"use strict";

const API_BASE   = "http://127.0.0.1:8000";
const REVIEW_URL = `${API_BASE}/review/demo`;

// ── Ordered list of agents for the execution-status section ───────────────
const AGENT_ORDER = [
  { name: "Cash Flow Agent",             step: "Step 1" },
  { name: "Financial Risk Agent",        step: "Step 2" },
  { name: "Document Agent",              step: "Step 3" },
  { name: "Underwriting Preparation Agent", step: "Step 4" },
];

// ── Metric cards definition ────────────────────────────────────────────────
// Each entry describes one card in section B.
// path: dot-separated path into final_report.liquidity_analysis.metrics
// format: "currency" | "percent" | "number"
// variant: "alert" | "warn" | "ok" | "" (affects value colour)
// alertIf: fn(value) => bool — if true AND value > 0, use the given variant
const METRIC_CARDS = [
  {
    label:    "Credit Utilization",
    path:     "credit_utilization_pct",
    format:   "percent",
    variantFn: (v) => parseFloat(v) >= 80 ? "warn" : "ok",
  },
  {
    label:    "Available Credit",
    path:     "available_credit",
    format:   "currency",
    variantFn: (v) => parseFloat(v) === 0 ? "warn" : "ok",
  },
  {
    label:    "Bank Balance",
    path:     "bank_balance",        // from business_overview
    isOverview: true,
    format:   "currency",
    variantFn: () => "",
  },
  {
    label:    "Upcoming Obligations",
    path:     "upcoming_obligations",
    format:   "currency",
    variantFn: () => "",
  },
  {
    label:    "Immediate Funding Gap",
    path:     "immediate_funding_gap",
    format:   "currency",
    variantFn: (v) => parseFloat(v) > 0 ? "warn" : "ok",
  },
  {
    label:    "Remaining Funding Gap",
    path:     "remaining_funding_gap",
    format:   "currency",
    variantFn: (v) => parseFloat(v) > 0 ? "alert" : "ok",
  },
];

// ── Utility: format values for display ────────────────────────────────────

function formatCurrency(raw) {
  const n = parseFloat(raw);
  if (isNaN(n)) return raw;
  return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatPercent(raw) {
  const n = parseFloat(raw);
  if (isNaN(n)) return raw;
  return n.toFixed(2) + "%";
}

function formatValue(raw, fmt) {
  if (fmt === "currency") return formatCurrency(raw);
  if (fmt === "percent")  return formatPercent(raw);
  return String(raw ?? "—");
}

/** Convert a snake_case or camelCase key into a readable label. */
function humanKey(key) {
  return key
    .replace(/_pct$/, " %")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Safely create a text node — prevents XSS via innerHTML assignment. */
function text(str) {
  return document.createTextNode(String(str ?? ""));
}

/** Create an element with optional className and text content. */
function el(tag, className, textContent) {
  const e = document.createElement(tag);
  if (className)   e.className = className;
  if (textContent !== undefined) e.appendChild(text(textContent));
  return e;
}

// ── UI state helpers ───────────────────────────────────────────────────────

function showLoading(show) {
  document.getElementById("loading-overlay").hidden = !show;
}

function showError(message) {
  document.getElementById("error-message").textContent = message;
  document.getElementById("error-panel").hidden  = false;
  document.getElementById("dashboard").hidden    = true;
}

function showDashboard() {
  document.getElementById("error-panel").hidden  = true;
  document.getElementById("dashboard").hidden    = false;
}

function clearDashboard() {
  [
    "metrics-grid", "agent-grid", "liquidity-list",
    "warnings-list", "positives-list", "doc-list",
    "evidence-grid", "questions-list",
  ].forEach((id) => {
    const node = document.getElementById(id);
    if (node) node.innerHTML = "";
  });
  document.getElementById("advisory-banner").textContent = "";
}

// ── Section A: Business bar ────────────────────────────────────────────────

function renderBizBar(data) {
  const bizName      = document.getElementById("biz-name");
  const badgeEl      = document.getElementById("workflow-badge");
  const bizMetaEl    = document.getElementById("biz-meta");

  bizName.textContent = data.business_name || "—";

  const status = data.workflow_status || "unknown";
  badgeEl.textContent = status.toUpperCase();
  badgeEl.className   = `workflow-badge ${status}`;

  const agentCount = (data.agents_executed || []).length;
  bizMetaEl.textContent = `${agentCount} agents executed`;
}

// ── Advisory banner ────────────────────────────────────────────────────────

function renderAdvisoryBanner(data) {
  const banner = document.getElementById("advisory-banner");
  // Pull human_review_requirement from the top-level result, or fallback to the report.
  const msg =
    data.human_review_requirement ||
    data.final_report?.human_review_requirement ||
    "This report is for human review only.";
  banner.textContent = msg;
}

// ── Section B: Financial overview metrics ─────────────────────────────────

function renderMetrics(data) {
  const grid    = document.getElementById("metrics-grid");
  const metrics = data.final_report?.liquidity_analysis?.metrics || {};
  const overview = data.final_report?.business_overview || {};

  METRIC_CARDS.forEach(({ label, path, format, variantFn, isOverview }) => {
    const raw     = isOverview ? overview[path] : metrics[path];
    const display = formatValue(raw, format);
    const variant = variantFn ? variantFn(raw) : "";

    const card = el("div", `metric-card${variant ? " metric--" + variant : ""}`);
    card.appendChild(el("div", "metric-label", label));
    card.appendChild(el("div", "metric-value", display));
    grid.appendChild(card);
  });
}

// ── Section C: Agent execution status ─────────────────────────────────────

function renderAgents(data) {
  const grid     = document.getElementById("agent-grid");
  const statuses = data.agent_statuses || {};

  AGENT_ORDER.forEach(({ name, step }) => {
    const status = statuses[name] || "pending";

    const row       = el("div", "agent-row");
    const nameWrap  = el("div");
    const nameSpan  = el("span", "agent-name", name);
    const stepSpan  = el("span", "agent-step", `· ${step}`);
    nameWrap.appendChild(nameSpan);
    nameWrap.appendChild(stepSpan);

    const pill = el("span", `agent-status-pill ${status}`, status);

    row.appendChild(nameWrap);
    row.appendChild(pill);
    grid.appendChild(row);
  });
}

// ── Section D: Financial findings ─────────────────────────────────────────

function renderList(listId, items, iconChar) {
  const ul = document.getElementById(listId);
  if (!items || items.length === 0) {
    ul.appendChild(el("li", "", "None identified."));
    return;
  }
  items.forEach((text_) => {
    const li   = el("li");
    if (iconChar) {
      const icon = el("i", "item-icon", iconChar);
      li.appendChild(icon);
    }
    li.appendChild(text(text_));
    ul.appendChild(li);
  });
}

function renderFindings(data) {
  const report = data.final_report;
  if (!report) return;

  renderList(
    "liquidity-list",
    report.liquidity_analysis?.summary,
    null
  );
  renderList(
    "warnings-list",
    report.financial_indicators?.warning_signs,
    "⚠"
  );
  renderList(
    "positives-list",
    report.financial_indicators?.positive_indicators,
    "✓"
  );
}

// ── Section E: Document checklist ─────────────────────────────────────────

function renderDocuments(data) {
  const docComp = data.final_report?.document_completeness;
  if (!docComp) return;

  const completenessRow = document.getElementById("doc-completeness-row");
  const received = docComp.received_documents || [];
  const missing  = docComp.missing_documents  || [];
  const total    = received.length + missing.length;
  completenessRow.textContent =
    `${received.length} of ${total} required documents received.` +
    (docComp.is_complete ? " All documents on file." : " Action required: missing documents.");

  const docList = document.getElementById("doc-list");

  received.forEach((name) => {
    const li   = el("li", "doc-item");
    li.appendChild(el("span", "doc-item-name", name));
    li.appendChild(el("span", "doc-pill received", "Received"));
    docList.appendChild(li);
  });

  missing.forEach((name) => {
    const li = el("li", "doc-item doc-item--missing");
    li.appendChild(el("span", "doc-item-name", name));
    li.appendChild(el("span", "doc-pill missing", "Missing"));
    docList.appendChild(li);
  });
}

// ── Section F: Supporting evidence ────────────────────────────────────────

function renderEvidence(data) {
  const grid     = document.getElementById("evidence-grid");
  const evidence = data.final_report?.supporting_evidence || {};

  const entries = Object.entries(evidence);
  if (entries.length === 0) {
    grid.appendChild(el("p", "", "No supporting evidence available."));
    return;
  }

  entries.forEach(([key, value]) => {
    // Skip redundant threshold and days entries in this view.
    if (key === "elevated_utilization_threshold_pct") return;

    const item  = el("div", "evidence-item");
    const label = el("span", "evidence-key", humanKey(key));
    // Format currencies (keys ending in known monetary names) vs plain numbers.
    const isMonetary = /credit|balance|gap|obligation|receivable/.test(key);
    const isPercent  = key.endsWith("_pct");
    const display    = isPercent
      ? formatPercent(value)
      : isMonetary
        ? formatCurrency(value)
        : String(value);
    const val = el("span", "evidence-val", display);
    item.appendChild(label);
    item.appendChild(val);
    grid.appendChild(item);
  });
}

// ── Section G: Outstanding questions ──────────────────────────────────────

function renderQuestions(data) {
  const ol        = document.getElementById("questions-list");
  const questions = data.final_report?.all_unresolved_questions || [];

  if (questions.length === 0) {
    ol.appendChild(el("li", "", "No outstanding questions identified."));
    return;
  }

  questions.forEach(({ source, question }) => {
    const li     = el("li");
    const src    = el("span", "q-source", source);
    li.appendChild(src);
    li.appendChild(text(question));
    ol.appendChild(li);
  });
}

// ── Workflow failure display ───────────────────────────────────────────────

function renderFailedWorkflow(data) {
  // Show the business bar and advisory even on failure.
  renderBizBar(data);
  renderAdvisoryBanner(data);
  renderAgents(data);
  showDashboard();

  // Surface the error prominently above the agent grid.
  const failedAgent = data.failed_agent ? ` (${data.failed_agent})` : "";
  const errorMsg    = data.error || "An unknown error occurred in the agent workflow.";
  showError(`Workflow failed${failedAgent}: ${errorMsg}`);
}

// ── Main render entry point ────────────────────────────────────────────────

function renderDashboard(data) {
  clearDashboard();

  if (!data || data.workflow_status !== "completed" || !data.final_report) {
    renderFailedWorkflow(data || {});
    return;
  }

  renderBizBar(data);
  renderAdvisoryBanner(data);
  renderMetrics(data);
  renderAgents(data);
  renderFindings(data);
  renderDocuments(data);
  renderEvidence(data);
  renderQuestions(data);

  showDashboard();
}

// ── API fetch ──────────────────────────────────────────────────────────────

async function runReview() {
  // Disable the button while fetching to avoid duplicate requests.
  const btn = document.getElementById("btn-run-review");
  if (btn) btn.disabled = true;

  showLoading(true);
  document.getElementById("error-panel").hidden  = true;
  document.getElementById("dashboard").hidden    = true;

  try {
    const response = await fetch(REVIEW_URL);

    if (!response.ok) {
      // HTTP error — surface status code but do not show raw server error body.
      throw new Error(
        `The server returned HTTP ${response.status} (${response.statusText}). ` +
        "Check that the backend is running correctly."
      );
    }

    const data = await response.json();
    renderDashboard(data);

  } catch (err) {
    if (err instanceof TypeError) {
      // Network-level failure (backend not running, CORS, etc.)
      showError(
        "Could not reach the backend API. " +
        "Make sure the FastAPI server is running on http://127.0.0.1:8000 " +
        "and try again."
      );
    } else {
      showError(err.message || "An unexpected error occurred.");
    }
    document.getElementById("error-panel").hidden = false;
  } finally {
    showLoading(false);
    if (btn) btn.disabled = false;
  }
}

// ── Auto-run on page load ──────────────────────────────────────────────────
runReview();
