// Truth History SDK - content script
// 지원 LLM 사이트의 어시스턴트 메시지를 관찰하여 한국사 고증 검증 배지를 삽입한다.

const SITE_SELECTORS = {
  "chatgpt.com": ['[data-message-author-role="assistant"]', 'article[data-testid^="conversation-turn"] .markdown:last-child'],
  "chat.openai.com": ['[data-message-author-role="assistant"]'],
  "claude.ai": ['[data-testid="assistant-message"]', 'div.font-claude-message', 'div.prose', '[data-testid="turn"]'],
  "gemini.google.com": ['message-content', 'model-response', '.model-response-text', '.response-container-content', '.markdown'],
  "aistudio.google.com": ['.ms-en-GB', '.markdown', 'ms-chat-turn'],
};

function selectorsForHost() {
  const h = location.hostname;
  for (const key of Object.keys(SITE_SELECTORS)) {
    if (h.includes(key)) return SITE_SELECTORS[key];
  }
  return null;
}

function getText(node) {
  return (node.innerText || node.textContent || "").trim();
}

function scanText(text) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage({ type: "TH_SCAN", text }, (resp) => resolve(resp));
    } catch (e) {
      resolve({ ok: false, error: String(e) });
    }
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

function riskColor(level) {
  return ({ LOW: "#16a34a", MEDIUM: "#d97706", HIGH: "#dc2626", CRITICAL: "#b91c1c" })[level] || "#64748b";
}

function buildBanner(report) {
  const d = (report && report.decision) || {};
  const cred = Math.round(((d.credibility_score == null ? 1 : d.credibility_score)) * 100);
  const level = d.risk_level || "LOW";
  const reasons = (report && report.explanations ? report.explanations : []).map((e) => e.message).filter(Boolean);
  const wrap = document.createElement("div");
  wrap.className = "th-ext-banner";
  wrap.style.borderLeftColor = riskColor(level);
  const reasonsHtml = reasons.length
    ? `<ul>${reasons.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>`
    : "<p class=\"th-ext-none\">특이 역사 왜곡 징후 없음</p>";
  wrap.innerHTML =
    `<div class="th-ext-head">
      <span class="th-ext-logo">🛡️ Truth History</span>
      <span class="th-ext-cred">신뢰도 ${cred}% · ${escapeHtml(level)}</span>
      <span class="th-ext-tag ${d.is_manipulated ? "th-ext-bad" : "th-ext-good"}">
        ${d.is_manipulated ? "역사 왜곡·할루시네이션 의심" : "정상"}
      </span>
    </div>
    <div class="th-ext-reasons">${reasonsHtml}</div>`;
  wrap.style.cursor = "pointer";
  wrap.title = "클릭 시 상세 리포트·근거 자료를 표시합니다";
  wrap.addEventListener("click", () => showDetail(report));
  return wrap;
}
function buildDetailPanel(report) {
  const d = (report && report.decision) || {};
  const m = (report && report.metrics) || {};
  const cred = Math.round(((d.credibility_score == null ? 1 : d.credibility_score)) * 100);
  const reasons = (report && report.explanations ? report.explanations : []).map((e) => e.message).filter(Boolean);
  const evidence = (report && report.evidence) || [];
  const ref = (report && report.reference) || {};
  const panel = document.createElement("div");
  panel.id = "th-ext-detail";
  const refHtml = ref.snippet
    ? `<div class="th-ext-d-sec">📖 참고 사료 (수정된 진실 근거)</div>
       <div class="th-ext-d-ref"><span class="th-ext-d-src">${escapeHtml(ref.source || "")}</span> ${escapeHtml(ref.snippet)}
       ${ref.url ? `<a class="th-ext-d-link" href="${escapeHtml(ref.url)}" target="_blank" rel="noopener">원문 보기 ↗</a>` : ""}</div>` : "";
  const evHtml = evidence.length
    ? `<div class="th-ext-d-sec">🔗 근거 자료 웹사이트</div>
       <ul class="th-ext-d-list">${evidence.map((e) => `<li>${e.url ? `<a class="th-ext-d-link" href="${escapeHtml(e.url)}" target="_blank" rel="noopener">${escapeHtml(e.title || e.source)}</a>` : `<span>${escapeHtml(e.title || e.source)}</span>`} <span class="th-ext-d-src">(${escapeHtml(e.source || "")})</span></li>`).join("")}</ul>` : "";
  panel.innerHTML =
    `<div class="th-ext-d-head"><span>🛡️ Truth History 상세 리포트</span><button class="th-ext-d-x">✕</button></div>
     <div class="th-ext-d-row"><b>신뢰도</b> ${cred}% · ${escapeHtml(d.risk_level || "LOW")} — ${d.is_manipulated ? "역사 왜곡·할루시네이션 의심" : "정상"}</div>
     <div class="th-ext-d-row"><b>AI 생성/합성 확률</b> ${Math.round(((m.ai_generation_probability == null ? 0 : m.ai_generation_probability)) * 100)}%</div>
     <div class="th-ext-d-sec">📋 판정 근거</div>
     <ul class="th-ext-d-list">${reasons.length ? reasons.map((r) => `<li>${escapeHtml(r)}</li>`).join("") : "<li>특이 징후 없음</li>"}</ul>
     ${refHtml}${evHtml}`;
  panel.querySelector(".th-ext-d-x").onclick = () => panel.remove();
  return panel;
}

function showDetail(report) {
  const old = document.getElementById("th-ext-detail");
  if (old) old.remove();
  document.body.appendChild(buildDetailPanel(report));
}

async function scanNode(node) {
  if (!node || node.dataset.thScanned) return;
  const text = getText(node);
  if (text.length < 15) return;
  node.dataset.thScanned = "1";
  const resp = await scanText(text);
  if (resp && resp.ok && resp.report) {
    try {
      node.prepend(buildBanner(resp.report));
    } catch (_) { /* shadow DOM 등 삽입 불가 시 무시 */ }
    chrome.storage.local.set({
      lastReport: resp.report,
      lastText: text.slice(0, 240),
      lastTs: Date.now(),
    });
  } else if (resp && !resp.ok) {
    node.dataset.thScanned = ""; // 실패 시 재시도 허용
    showError(resp.error || "검증 실패");
  }
}

function scanUnscanned() {
  const sels = selectorsForHost();
  if (!sels) return;
  const seen = new Set();
  for (const sel of sels) {
    document.querySelectorAll(sel).forEach((n) => {
      if (!seen.has(n)) { seen.add(n); scanNode(n); }
    });
  }
}

let timer = null;
const observer = new MutationObserver(() => {
  if (timer) return;
  timer = setTimeout(() => { timer = null; scanUnscanned(); }, 1500);
});

function start() {
  chrome.storage.local.get({ autoScan: true }, ({ autoScan }) => {
    if (!autoScan) return;
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(scanUnscanned, 2500);
  });
}

// 우클릭 선택 텍스트 검사 결과 → 플로팅 패널
function showResult(report) {
  removePanel();
  const panel = document.createElement("div");
  panel.id = "th-ext-panel";
  panel.appendChild(buildBanner(report));
  const close = document.createElement("button");
  close.className = "th-ext-close";
  close.textContent = "닫기";
  close.onclick = removePanel;
  panel.appendChild(close);
  document.body.appendChild(panel);
}

function removePanel() {
  const old = document.getElementById("th-ext-panel");
  if (old) old.remove();
}

function showError(message) {
  removePanel();
  const panel = document.createElement("div");
  panel.id = "th-ext-panel";
  panel.className = "th-ext-err";
  panel.innerHTML = `<div class="th-ext-head"><span class="th-ext-logo">🛡️ Truth History</span></div>
    <p>검증 엔진 연결 실패: ${escapeHtml(String(message))}</p>
    <p class="th-ext-hint">Truth History 백엔드(<code>th api</code>)가 실행 중인지, popup의 API 주소가 올바른지 확인하세요.</p>`;
  const close = document.createElement("button");
  close.className = "th-ext-close";
  close.textContent = "닫기";
  close.onclick = removePanel;
  panel.appendChild(close);
  document.body.appendChild(panel);
  setTimeout(removePanel, 8000);
}

chrome.runtime.onMessage.addListener((msg) => {
  if (!msg) return;
  if (msg.type === "TH_SHOW_RESULT" && msg.report) showResult(msg.report);
  if (msg.type === "TH_ERROR" && msg.message) showError(msg.message);
});

start();
