const DEFAULTS = { autoScan: true, backendMode: "auto", customApiBase: "http://localhost:8000" };

const $ = (id) => document.getElementById(id);

function riskClass(level) {
  if (level === "CRITICAL" || level === "HIGH") return "bad";
  if (level === "MEDIUM") return "warn";
  return "ok";
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
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

// ── 백엔드 설정 UI ─────────────────────────────────────────────
function toggleCustomUrl(visible) {
  $("customApiWrap").style.display = visible ? "block" : "none";
}

$("backendSelect").addEventListener("change", ({ target }) => {
  toggleCustomUrl(target.value === "custom");
});

$("checkBackend").addEventListener("click", () => {
  $("status").innerHTML = '<span class="muted">백엔드 상태 확인 중…</span>';
  chrome.runtime.sendMessage({ type: "TH_GET_BACKEND_STATUS" }, (status) => {
    // 서비스 워커 미기동 등으로 실패한 경우 lastError를 반드시 소비해
    // "Unchecked runtime.lastError" 콘솔 에러를 방지한다.
    if (chrome.runtime.lastError || !status || !status.ok) {
      $("status").innerHTML =
        '<span class="bad">백엔드 상태 조회 실패</span>' +
        '<div class="muted" style="margin-top:2px;">확장 프로그램을 다시 로드하거나 잠시 후 재시도하세요.</div>';
      return;
    }
    const currentHtml = `현재 백엔드: <b>${escapeHtml(status.currentApi)}</b>`;
    const localHtml = status.isLocalActive
      ? `로컬 활성화 <span class="ok">${escapeHtml(status.localApi)}</span>`
      : `로컬 사용불가 <span class="bad">${escapeHtml(status.localApi)}</span>`;
    $("status").innerHTML = `${currentHtml}<br>${localHtml}`;
  });
});

// ── 초기 로드: 저장된 설정 반영 ────────────────────────────────
chrome.storage.local.get(DEFAULTS, (s) => {
  $("autoScan").checked = s.autoScan !== false;
  const select = $("backendSelect");
  const input = $("customApiInput");
  select.value = s.backendMode || "auto";
  input.value = s.customApiBase || DEFAULTS.customApiBase;
  toggleCustomUrl(select.value === "custom");

  chrome.storage.local.get(["lastReport"], (r) => {
    if (r.lastReport) renderStatus(r.lastReport);
  });
});

// ── 설정 저장 ──────────────────────────────────────────────────
$("save").addEventListener("click", () => {
  const payload = {
    autoScan: $("autoScan").checked,
    backendMode: $("backendSelect").value,
    customApiBase: ($("customApiInput").value || DEFAULTS.customApiBase).trim().replace(/\/+$/, ""),
  };
  chrome.storage.local.set(payload, () => {
    const btn = $("save");
    const prev = btn.textContent;
    btn.textContent = "저장됨 ✓";
    setTimeout(() => { btn.textContent = prev; }, 1200);
  });
});
