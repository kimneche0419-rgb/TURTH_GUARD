// Truth History SDK - background service worker
// LLM 역사 할루시네이션 검증 요청을 Truth History REST API로 중계한다.

// 배포된 Truth History 백엔드(Vercel) — 확장 프로그램은 별도 백엔드/API 주소 설정 없이 즉시 동작.
// 로컬 백엔드로 개발하려면 이 상수를 http://localhost:8000 로 변경.
const API_BASE = "https://platy-rho.vercel.app";

async function scanText(text) {
  const res = await fetch(`${API_BASE}/api/v1/scan/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`API 오류 ${res.status}: ${detail.slice(0, 160)}`);
  }
  return res.json();
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "th-scan-selection",
    title: "Truth History: 이 텍스트 역사 할루시네이션 검사",
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "th-scan-selection" || !info.selectionText) return;
  try {
    const report = await scanText(info.selectionText);
    await chrome.storage.local.set({
      lastReport: report,
      lastText: info.selectionText.slice(0, 240),
      lastTs: Date.now(),
    });
    if (tab && tab.id) {
      chrome.tabs.sendMessage(tab.id, { type: "TH_SHOW_RESULT", report });
    }
  } catch (e) {
    if (tab && tab.id) {
      chrome.tabs.sendMessage(tab.id, { type: "TH_ERROR", message: String(e && e.message ? e.message : e) });
    }
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "TH_SCAN") {
    scanText(msg.text)
      .then((report) => sendResponse({ ok: true, report }))
      .catch((e) => sendResponse({ ok: false, error: String(e && e.message ? e.message : e) }));
    return true; // keep channel open for async response
  }
});
