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

// 이미지·영상 URL을 가져와 /api/v1/scan/media(멀티파트)로 검증한다.
async function scanMediaUrl(url, kind) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`미디어 가져오기 실패 ${res.status}`);
  const blob = await res.blob();
  let name = "";
  try {
    name = decodeURIComponent(new URL(url).pathname.split("/").filter(Boolean).pop() || "");
  } catch (_) { name = ""; }
  const extMatch = name.match(/\.(jpg|jpeg|png|webp|mp4|avi|mov|mkv|wav|mp3|m4a|flac)$/i);
  const fallbackExt = kind === "video" ? "mp4" : kind === "audio" ? "wav" : "jpg";
  const filename = extMatch ? name : `${name || "truthhistory-media"}.${fallbackExt}`;
  const file = new File([blob], filename, { type: blob.type || "application/octet-stream" });
  const fd = new FormData();
  fd.append("file", file);
  const api = await fetch(`${API_BASE}/api/v1/scan/media`, { method: "POST", body: fd });
  if (!api.ok) {
    const detail = await api.text().catch(() => "");
    throw new Error(`API 오류 ${api.status}: ${detail.slice(0, 160)}`);
  }
  return api.json();
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "th-scan-selection",
    title: "Truth History: 이 텍스트 역사 할루시네이션 검사",
    contexts: ["selection"],
  });
  chrome.contextMenus.create({
    id: "th-scan-image",
    title: "Truth History: 이 이미지 위변조(합성) 검사",
    contexts: ["image"],
  });
  chrome.contextMenus.create({
    id: "th-scan-video",
    title: "Truth History: 이 영상 딥페이크 검사",
    contexts: ["video"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "th-scan-selection" && info.selectionText) {
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
    return;
  }
  if ((info.menuItemId === "th-scan-image" || info.menuItemId === "th-scan-video") && info.srcUrl) {
    const kind = info.menuItemId === "th-scan-video" ? "video" : "image";
    try {
      const report = await scanMediaUrl(info.srcUrl, kind);
      await chrome.storage.local.set({
        lastReport: report,
        lastText: `${kind === "video" ? "영상" : "이미지"}: ${info.srcUrl.slice(0, 200)}`,
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
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "TH_SCAN") {
    scanText(msg.text)
      .then((report) => sendResponse({ ok: true, report }))
      .catch((e) => sendResponse({ ok: false, error: String(e && e.message ? e.message : e) }));
    return true; // keep channel open for async response
  }
  if (msg && msg.type === "TH_SCAN_MEDIA") {
    scanMediaUrl(msg.url, msg.kind)
      .then((report) => sendResponse({ ok: true, report }))
      .catch((e) => sendResponse({ ok: false, error: String(e && e.message ? e.message : e) }));
    return true;
  }
});