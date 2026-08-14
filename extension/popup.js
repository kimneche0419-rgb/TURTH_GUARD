const DEFAULTS = { apiUrl: "https://platy-rho.vercel.app", autoScan: true, threshold: 0.5 };


const $ = (id) => document.getElementById(id);

function riskClass(level) {
  if (level === "CRITICAL" || level === "HIGH") return "bad";
  if (level === "MEDIUM") return "warn";
  return "ok";
}

function renderStatus(report) {
  const el = $("status");
  if (!report) {
    el.innerHTML = '<span class="muted">최근 검사 결과가 여기에 표시됩니다.</span>';
    return;
  }
  const d = report.decision || {};
  const cred = Math.round((d.credibility_score == null ? 1 : d.credibility_score) * 100);
  const reasons = (report.explanations || []).map((e) => e.message).filter(Boolean);
  const reasonsHtml = reasons.length
    ? `<ul class="reasons">${reasons.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>`
    : '<p class="muted" style="margin:6px 0 0 0;">특이 역사 왜곡 징후 없음</p>';
  el.innerHTML =
    `<div class="cred ${riskClass(d.risk_level)}">신뢰도 ${cred}% · ${escapeHtml(d.risk_level || "LOW")}</div>` +
    `<div class="muted" style="margin-top:2px;">${d.is_manipulated ? "역사 왜곡·할루시네이션 의심" : "정상"}</div>` +
    reasonsHtml;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

chrome.storage.local.get([...Object.keys(DEFAULTS), "lastReport", "lastText"], (s) => {
  $("apiUrl").value = s.apiUrl || DEFAULTS.apiUrl;
  $("autoScan").checked = s.autoScan !== false;
  if (s.lastReport) renderStatus(s.lastReport);
});

$("save").addEventListener("click", () => {
  const payload = {
    apiUrl: $("apiUrl").value.trim() || DEFAULTS.apiUrl,
    autoScan: $("autoScan").checked,
  };
  chrome.storage.local.set(payload, () => {
    const btn = $("save");
    const prev = btn.textContent;
    btn.textContent = "저장됨 ✓";
    setTimeout(() => { btn.textContent = prev; }, 1200);
  });
});
