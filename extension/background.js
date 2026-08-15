// Chrome MV3 service worker: chrome.tabs.sendMessage / scripting API가 내부적으로
// Promise를 생성해 reject 시 "Uncaught (in promise)" 로 보고하는 Chrome 런타임 특성 대응.
// 커넥션 실패 에러는 정상 동작(content script 미주입 탭)이므로 전역에서 억제한다.
self.addEventListener("unhandledrejection", (ev) => {
  const reason = ev && ev.reason;
  const msg = String((reason && (reason.message || reason)) || "");
  if (
    msg.includes("Could not establish connection") ||
    msg.includes("Receiving end does not exist") ||
    msg.includes("message channel closed") ||
    msg.includes("message port closed") ||
    msg.includes("The message port closed before a response was received")
  ) {
    ev.preventDefault();  // DevTools 에러 패널에서 제거
  }
});

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

// content script가 없는 탭에서도 메시지를 전달.
// ★ async/await + try/catch로 감싸 Promise rejection이 DevTools로 누출되지 않도록 처리.
async function sendToTab(tabId, msg) {
  if (!tabId) return;
  try {
    await chrome.tabs.sendMessage(tabId, msg);
  } catch (_err) {
    // content script 미주입 탭 -> executeScript로 즉시 주입 후 재전송
    try {
      await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
      await chrome.scripting.insertCSS({ target: { tabId }, files: ["content.css"] }).catch(() => {});
      await new Promise((r) => setTimeout(r, 250));
      await chrome.tabs.sendMessage(tabId, msg);
    } catch (_) {
      // chrome:// 등 주입 불가 탭이거나 탭 종료 시 정상 무시
    }
  }
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

const YT_URL_RE = /(?:youtube\.com\/(?:watch\?[^#]*v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{6,})/;
const RISK_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

function isYoutubeUrl(u) {
  return !!(u && YT_URL_RE.test(u));
}

// YouTube 영상 검증 — oEmbed 메타데이터(제목·채널·썸네일) 기반:
// ① 썸네일 이미지 ELA/합성 분석(/scan/media) ② 제목·채널명 텍스트 고증(/scan/text) 병합.
async function scanYoutube(url) {
  const m = url.match(YT_URL_RE);
  if (!m) throw new Error("YouTube URL이 아닙니다");
  const oe = await fetch(
    `https://www.youtube.com/oembed?url=${encodeURIComponent(url)}&format=json`
  );
  if (!oe.ok) throw new Error(`YouTube 정보 조회 실패 ${oe.status}`);
  const meta = await oe.json();

  const [thumbReport, titleReport] = await Promise.all([
    meta.thumbnail_url ? scanMediaUrl(meta.thumbnail_url, "image").catch(() => null) : null,
    scanText(`"${meta.title}" — ${meta.author_name} 채널의 YouTube 영상`).catch(() => null),
  ]);

  const exps = [
    ...((thumbReport && thumbReport.explanations) || []),
    ...((titleReport && titleReport.explanations) || []),
  ];
  const creds = [thumbReport, titleReport]
    .filter(Boolean)
    .map((r) => (r.decision && r.decision.credibility_score != null ? r.decision.credibility_score : 1));
  const risks = [thumbReport, titleReport]
    .filter(Boolean)
    .map((r) => (r.decision && r.decision.risk_level) || "LOW");
  const worst = risks.sort((a, b) => RISK_ORDER.indexOf(b) - RISK_ORDER.indexOf(a))[0] || "LOW";
  const cred = creds.length ? Math.min(...creds) : 0.5;
  const manipulated = !!(thumbReport || titleReport) &&
    ((thumbReport && thumbReport.decision && thumbReport.decision.is_manipulated) ||
     (titleReport && titleReport.decision && titleReport.decision.is_manipulated));

  return {
    target_file: meta.title,
    media_type: "video(youtube)",
    decision: { is_manipulated: manipulated, credibility_score: cred, risk_level: worst },
    metrics: {
      ai_generation_probability: (titleReport && titleReport.metrics && titleReport.metrics.ai_generation_probability) || 0,
      editing_artifact_score: (thumbReport && thumbReport.metrics && thumbReport.metrics.editing_artifact_score) || 0,
      semantic_consistency_score: (titleReport && titleReport.metrics && titleReport.metrics.semantic_consistency_score) || 0,
    },
    explanations: exps.length ? exps : [{ code: "YOUTUBE_SCAN", severity: "WARNING", message: "YouTube 메타데이터(썸네일·제목) 기반 검증 결과 없음 — 중립 처리", location: "global" }],
    evidence: (titleReport && titleReport.evidence) || [],
    reference: (titleReport && titleReport.reference) || {},
    youtube: { url, title: meta.title, author: meta.author_name },
  };
}

chrome.runtime.onInstalled.addListener(() => {
  // 재설치/업데이트/새로고침 시 중복 ID 에러 방지 — 기존 메뉴 전부 제거 후 재생성
  chrome.contextMenus.removeAll(() => {
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
      title: "Truth History: 이 영상(YouTube) 딥페이크·왜곡 검사",
      contexts: ["video", "frame"],  // "link" 제거 — 모든 링크에 노출되어 혼란
    });
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const tabId = tab && tab.id;
  if (!tabId) return;

  if (info.menuItemId === "th-scan-selection" && info.selectionText) {
    try {
      const report = await scanText(info.selectionText);
      await chrome.storage.local.set({
        lastReport: report,
        lastText: info.selectionText.slice(0, 240),
        lastTs: Date.now(),
      }).catch(() => {});
      await sendToTab(tabId, { type: "TH_SHOW_RESULT", report });
    } catch (e) {
      await sendToTab(tabId, { type: "TH_ERROR", message: String(e && e.message ? e.message : e) });
    }
    return;
  }
  if (info.menuItemId === "th-scan-image" && info.srcUrl) {
    try {
      const report = await scanMediaUrl(info.srcUrl, "image");
      await chrome.storage.local.set({
        lastReport: report,
        lastText: `이미지: ${info.srcUrl.slice(0, 200)}`,
        lastTs: Date.now(),
      }).catch(() => {});
      await sendToTab(tabId, { type: "TH_SHOW_RESULT", report });
    } catch (e) {
      await sendToTab(tabId, { type: "TH_ERROR", message: String(e && e.message ? e.message : e) });
    }
    return;
  }
  if (info.menuItemId === "th-scan-video") {
    const target = info.srcUrl || info.frameUrl || info.pageUrl;
    if (!target) return;  // URL 없으면 무시
    try {
      const report = isYoutubeUrl(target)
        ? await scanYoutube(target)
        : await scanMediaUrl(target, "video");
      await chrome.storage.local.set({
        lastReport: report,
        lastText: `영상: ${String(target).slice(0, 200)}`,
        lastTs: Date.now(),
      }).catch(() => {});
      await sendToTab(tabId, { type: "TH_SHOW_RESULT", report });
    } catch (e) {
      await sendToTab(tabId, { type: "TH_ERROR", message: String(e && e.message ? e.message : e) });
    }
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg) return false;

  if (msg.type === "TH_SCAN") {
    scanText(msg.text)
      .then((report) => {
        try { sendResponse({ ok: true, report }); } catch (_) {}
      })
      .catch((e) => {
        try { sendResponse({ ok: false, error: String(e && e.message ? e.message : e) }); } catch (_) {}
      });
    return true; // keep channel open for async response
  }
  if (msg.type === "TH_SCAN_MEDIA") {
    scanMediaUrl(msg.url, msg.kind)
      .then((report) => {
        try { sendResponse({ ok: true, report }); } catch (_) {}
      })
      .catch((e) => {
        try { sendResponse({ ok: false, error: String(e && e.message ? e.message : e) }); } catch (_) {}
      });
    return true;
  }
  if (msg.type === "TH_SCAN_YOUTUBE") {
    scanYoutube(msg.url)
      .then((report) => {
        try { sendResponse({ ok: true, report }); } catch (_) {}
      })
      .catch((e) => {
        try { sendResponse({ ok: false, error: String(e && e.message ? e.message : e) }); } catch (_) {}
      });
    return true;
  }
  return false;
});