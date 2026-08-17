// Truth History SDK - content script
// 지원 LLM 사이트의 어시스턴트 메시지를 관찰하여 한국사 고증 검증 배지를 삽입한다.
(() => {
  if (window.__TH_GUARD_V2__) return;
  window.__TH_GUARD_V2__ = true;

  var TH_SELECTORS = {
    "chatgpt.com": ['[data-message-author-role="assistant"]', 'article[data-testid^="conversation-turn"] .markdown:last-child'],
    "chat.openai.com": ['[data-message-author-role="assistant"]'],
    "claude.ai": ['[data-testid="assistant-message"]', 'div.font-claude-message', 'div.prose', '[data-testid="turn"]'],
    "gemini.google.com": ['message-content', 'model-response', '.model-response-text', '.response-container-content', '.markdown'],
    "aistudio.google.com": ['.ms-en-GB', '.markdown', 'ms-chat-turn'],
  };

  function thSelectorsForHost() {
    var h = location.hostname;
    for (var key of Object.keys(TH_SELECTORS)) {
      if (h.includes(key)) return TH_SELECTORS[key];
    }
    return null;
  }

  function thGetText(node) {
    return (node.innerText || node.textContent || "").trim();
  }

  function thScanText(text) {
    return new Promise((resolve) => {
      try {
        chrome.runtime.sendMessage({ type: "TH_SCAN", text }, (resp) => {
          if (chrome.runtime.lastError) {
            resolve({ ok: false, error: chrome.runtime.lastError.message });
            return;
          }
          resolve(resp || { ok: false, error: "응답 없음" });
        });
      } catch (e) {
        resolve({ ok: false, error: String(e) });
      }
    });
  }

  function thEscapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[c]);
  }

  function thRiskColor(level) {
    return ({ LOW: "#16a34a", MEDIUM: "#d97706", HIGH: "#dc2626", CRITICAL: "#b91c1c" })[level] || "#64748b";
  }

  // 판정 라벨 — 점수·위험도와 연동된 3단계 (점수 낮으면 중립/주의 판정)
  function thVerdict(d) {
    var level = d.risk_level || "LOW";
    var score = d.credibility_score == null ? 1 : d.credibility_score;
    if (d.is_manipulated || level === "CRITICAL" || level === "HIGH") {
      return { text: "왜곡 의심", cls: "th-ext-bad" };
    }
    if (level === "MEDIUM" || score < 0.6) {
      return { text: "판정 보류(주의)", cls: "th-ext-warn" };
    }
    return { text: "정상", cls: "th-ext-good" };
  }

  // 시각 자료: 신뢰도 게이지 바 (리포트 공통 위젯)
  function thGauge(score, toneColor) {
    var pct = Math.round(Math.max(0, Math.min(1, score == null ? 0 : score)) * 100);
    return (
      '<div class="th-ext-gauge">' +
        '<div class="th-ext-gauge-fill" style="width:' + pct + '%; background:' + (toneColor || "#16a34a") + ';"></div>' +
      '</div>'
    );
  }

  // 시각 자료: 다각도 판별 막대 + 종합 노트
  function thPerspectivesHtml(report) {
    var p = report && report.perspectives;
    if (!p || !p.angles || !p.angles.length) return "";
    var s = p.summary || {};
    var toneColor = { ok: "#16a34a", warn: "#d97706", bad: "#dc2626", neutral: "#94a3b8" };
    var bars = p.angles.map(function (a) {
      var color = toneColor[a.tone] || "#94a3b8";
      var pct = a.score == null ? 0 : Math.round(a.score * 100);
      var scoreTxt = a.score == null ? "미판정" : pct + "%";
      return (
        '<div class="th-ext-angle">' +
          '<div class="th-ext-angle-head"><span class="th-ext-angle-name">' + thEscapeHtml(a.name) +
            '</span><span class="th-ext-angle-score" style="color:' + color + ';">' + thEscapeHtml(a.verdict) + " · " + scoreTxt + '</span></div>' +
          thGauge(a.score == null ? 0 : a.score, color) +
          '<div class="th-ext-angle-detail">' + thEscapeHtml(a.detail || "") + "</div>" +
        "</div>"
      );
    }).join("");
    return (
      '<div class="th-ext-d-sec">🔭 다각도 판별/분석 (' + (s.engaged_angles != null ? s.engaged_angles : "?") + "/" + (s.total_angles != null ? s.total_angles : "?") + "각도)</div>" +
      (s.note ? '<div class="th-ext-angle-note">' + thEscapeHtml(s.note) + "</div>" : "") +
      '<div class="th-ext-angles">' + bars + "</div>"
    );
  }

  // 지정학적 역사 왜곡 불허 사유 — 리포트 공통 콘텐츠
  function thSignificanceHtml(report) {
    var sig = report && report.significance;
    if (!sig || !sig.title) return "";
    var items = (sig.reasons || []).map(function (r) {
      return '<li><b>' + thEscapeHtml(r.tag) + "</b>: " + thEscapeHtml(r.detail) + "</li>";
    }).join("");
    return (
      '<div class="th-ext-d-sec">📌 ' + thEscapeHtml(sig.title) + "</div>" +
      (sig.summary ? '<div class="th-ext-sig-summary">' + thEscapeHtml(sig.summary) + "</div>" : "") +
      (items ? '<ul class="th-ext-d-list th-ext-sig-list">' + items + "</ul>" : "")
    );
  }

  function thBuildBanner(report) {
    var d = (report && report.decision) || {};
    var cred = Math.round(((d.credibility_score == null ? 1 : d.credibility_score)) * 100);
    var level = d.risk_level || "LOW";
    var reasons = (report && report.explanations ? report.explanations : []).map((e) => e.message).filter(Boolean);
    var wrap = document.createElement("div");
    wrap.className = "th-ext-banner";
    wrap.style.borderLeftColor = thRiskColor(level);
    var reasonsHtml = reasons.length
      ? `<ul>${reasons.map((r) => `<li>${thEscapeHtml(r)}</li>`).join("")}</ul>`
      : "<p class=\"th-ext-none\">특이 역사 왜곡 징후 없음</p>";
    wrap.innerHTML =
      `<div class="th-ext-head">
        <span class="th-ext-logo">🛡️ Truth History</span>
        <span class="th-ext-cred">신뢰도 ${cred}% · ${thEscapeHtml(level)}</span>
        <span class="th-ext-tag ${thVerdict(d).cls}">
          ${thEscapeHtml(thVerdict(d).text)}
        </span>
      </div>
      ${thGauge(d.credibility_score == null ? 1 : d.credibility_score, thRiskColor(level))}
      <div class="th-ext-reasons">${reasonsHtml}</div>`;
    wrap.style.cursor = "pointer";
    wrap.title = "클릭 시 상세 리포트·근거 자료를 표시합니다";
    wrap.addEventListener("click", () => thShowDetail(report));
    return wrap;
  }

  function thBuildDetailPanel(report) {
    var d = (report && report.decision) || {};
    var m = (report && report.metrics) || {};
    var cred = Math.round(((d.credibility_score == null ? 1 : d.credibility_score)) * 100);
    var reasons = (report && report.explanations ? report.explanations : []).map((e) => e.message).filter(Boolean);
    var evidence = (report && report.evidence) || [];
    var ref = (report && report.reference) || {};
    var panel = document.createElement("div");
    panel.id = "th-ext-detail";
    var refHtml = ref.snippet
      ? `<div class="th-ext-d-sec">📖 참고 사료 (수정된 진실 근거)</div>
         <div class="th-ext-d-ref"><span class="th-ext-d-src">${thEscapeHtml(ref.source || "")}</span> ${thEscapeHtml(ref.snippet)}
         ${ref.url ? `<a class="th-ext-d-link" href="${thEscapeHtml(ref.url)}" target="_blank" rel="noopener">원문 보기 ↗</a>` : ""}</div>` : "";
    var evHtml = evidence.length
      ? `<div class="th-ext-d-sec">🔗 근거 자료 웹사이트</div>
         <ul class="th-ext-d-list">${evidence.map((e) => `<li>${e.url ? `<a class="th-ext-d-link" href="${thEscapeHtml(e.url)}" target="_blank" rel="noopener">${thEscapeHtml(e.title || e.source)}</a>` : `<span>${thEscapeHtml(e.title || e.source)}</span>`} <span class="th-ext-d-src">(${thEscapeHtml(e.source || "")})</span></li>`).join("")}</ul>` : "";
    panel.innerHTML =
      `<div class="th-ext-d-head"><span>🛡️ Truth History 상세 리포트</span><button class="th-ext-d-x">✕</button></div>
       <div class="th-ext-d-row"><b>신뢰도</b> ${cred}% · ${thEscapeHtml(d.risk_level || "LOW")} — <span class="th-ext-tag ${thVerdict(d).cls}">${thEscapeHtml(thVerdict(d).text)}</span></div>
       ${thGauge(d.credibility_score == null ? 1 : d.credibility_score, thRiskColor(d.risk_level || "LOW"))}
       <div class="th-ext-d-row"><b>AI 생성/합성 확률</b> ${Math.round(((m.ai_generation_probability == null ? 0 : m.ai_generation_probability)) * 100)}%</div>
       <div class="th-ext-d-sec">📋 판정 근거</div>
       <ul class="th-ext-d-list">${reasons.length ? reasons.map((r) => `<li>${thEscapeHtml(r)}</li>`).join("") : "<li>특이 징후 없음</li>"}</ul>
       ${thPerspectivesHtml(report)}
       ${thSignificanceHtml(report)}
       ${refHtml}${evHtml}`;
    panel.querySelector(".th-ext-d-x").onclick = () => panel.remove();
    return panel;
  }

  function thShowDetail(report) {
    var old = document.getElementById("th-ext-detail");
    if (old) old.remove();
    document.body.appendChild(thBuildDetailPanel(report));
  }

  var TH_YT_PATTERN = /(?:youtube\.com\/(?:watch\?[^#]*v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{6,})/;

  // 단일 이미지 검증 및 배지 삽입
  function thScanImage(img) {
    img.dataset.thMediaScanned = "1";
    try {
      chrome.runtime.sendMessage({ type: "TH_SCAN_MEDIA", url: img.src, kind: "image" }, (resp) => {
        if (chrome.runtime.lastError) return;
        if (resp && resp.ok && resp.report) {
          try {
            var b = thBuildBanner(resp.report);
            b.classList.add("th-ext-media");
            b.insertAdjacentHTML("afterbegin", "<span style='margin-right:6px'>🖼️ 이미지 검증</span>");
            img.insertAdjacentElement("afterend", b);
          } catch (_) { /* 삽입 불가 시 무시 */ }
        }
      });
    } catch (_) {}
  }

  // 문서 전체 이미지 스캔
  function thScanImagesEverywhere() {
    document.querySelectorAll("img").forEach((img) => {
      if (!img.src || img.dataset.thMediaScanned) return;
      var w = img.naturalWidth || img.width || 0;
      if (w >= 64) {
        thScanImage(img);
      } else if (w === 0) {
        img.dataset.thMediaScanned = "pending";
        img.addEventListener("load", () => {
          if (img.dataset.thMediaScanned !== "pending") return;
          img.dataset.thMediaScanned = "";
          if ((img.naturalWidth || 0) >= 64) thScanImage(img);
        }, { once: true });
      }
    });
  }

  // 문서 전체 YouTube 링크·임베드 자동 검증
  function thScanYoutubeEverywhere() {
    var targets = new Map();
    document.querySelectorAll("a[href]").forEach((a) => {
      if (TH_YT_PATTERN.test(a.href) && !a.dataset.thYtScanned) {
        a.dataset.thYtScanned = "1";
        targets.set(a.href, a);
      }
    });
    document.querySelectorAll("iframe[src]").forEach((f) => {
      if (TH_YT_PATTERN.test(f.src) && !f.dataset.thYtScanned) {
        f.dataset.thYtScanned = "1";
        targets.set(f.src, f);
      }
    });
    for (var [url, el] of targets) {
      try {
        chrome.runtime.sendMessage({ type: "TH_SCAN_YOUTUBE", url }, (resp) => {
          if (chrome.runtime.lastError) return;
          if (resp && resp.ok && resp.report) {
            try {
              var b = thBuildBanner(resp.report);
              b.classList.add("th-ext-media");
              b.insertAdjacentHTML("afterbegin", "<span style='margin-right:6px'>🎬 YouTube 검증</span>");
              el.insertAdjacentElement("afterend", b);
            } catch (_) { /* 삽입 불가 시 무시 */ }
          }
        });
      } catch (_) {}
    }
  }

  async function thScanNode(node) {
    if (!node || node.dataset.thScanned) return;
    var text = thGetText(node);
    if (text.length < 15) return;
    node.dataset.thScanned = "1";
    var resp = await thScanText(text);
    if (resp && resp.ok && resp.report) {
      try {
        node.prepend(thBuildBanner(resp.report));
      } catch (_) { /* shadow DOM 등 삽입 불가 시 무시 */ }
      try {
        chrome.storage.local.set({
          lastReport: resp.report,
          lastText: text.slice(0, 240),
          lastTs: Date.now(),
        });
      } catch (_) {}
    } else if (resp && !resp.ok) {
      node.dataset.thScanned = ""; // 실패 시 재시도 허용
      thShowError(resp.error || "검증 실패");
    }
  }

  function thScanUnscanned() {
    // 텍스트 자동 스캔은 LLM 사이트 한정, 이미지·YouTube 스캔은 전 사이트 동작
    // (기존: LLM 사이트 아닌 경우 조기 return 때문에 전사이트 이미지 배지가 동작하지 않던 결함)
    var sels = thSelectorsForHost();
    if (sels) {
      var seen = new Set();
      for (var sel of sels) {
        document.querySelectorAll(sel).forEach((n) => {
          if (!seen.has(n)) { seen.add(n); thScanNode(n); }
        });
      }
    }
    thScanImagesEverywhere();
    thScanYoutubeEverywhere();
  }

  var thTimer = null;
  var thObserver = new MutationObserver(() => {
    if (thTimer) return;
    thTimer = setTimeout(() => { thTimer = null; thScanUnscanned(); }, 1500);
  });

  function thStart() {
    try {
      chrome.storage.local.get({ autoScan: true }, ({ autoScan }) => {
        if (!autoScan) return;
        if (document.body) {
          thObserver.observe(document.body, { childList: true, subtree: true });
          setTimeout(thScanUnscanned, 2500);
        }
      });
    } catch (_) {}
  }

  // 우클릭 선택 텍스트 검사 결과 → 플로팅 패널
  function thShowResult(report) {
    thRemovePanel();
    var panel = document.createElement("div");
    panel.id = "th-ext-panel";
    panel.appendChild(thBuildBanner(report));
    var close = document.createElement("button");
    close.className = "th-ext-close";
    close.textContent = "닫기";
    close.onclick = thRemovePanel;
    panel.appendChild(close);
    document.body.appendChild(panel);
  }

  function thRemovePanel() {
    var old = document.getElementById("th-ext-panel");
    if (old) old.remove();
  }

  function thShowError(message) {
    thRemovePanel();
    var panel = document.createElement("div");
    panel.id = "th-ext-panel";
    panel.className = "th-ext-err";
    panel.innerHTML = `<div class="th-ext-head"><span class="th-ext-logo">🛡️ Truth History</span></div>
      <p>검증 엔진 연결 실패: ${thEscapeHtml(String(message))}</p>
      <p class="th-ext-hint">Truth History 검증 서버(https://platy-rho.vercel.app)와의 네트워크 연결을 확인하세요.</p>`;
    var close = document.createElement("button");
    close.className = "th-ext-close";
    close.textContent = "닫기";
    close.onclick = thRemovePanel;
    panel.appendChild(close);
    document.body.appendChild(panel);
    setTimeout(thRemovePanel, 8000);
  }

  function thHandleMessage(msg) {
    if (!msg) return;
    if (msg.type === "TH_SHOW_RESULT" && msg.report) thShowResult(msg.report);
    if (msg.type === "TH_ERROR" && msg.message) thShowError(msg.message);
  }

  // 1. Chrome 확장 표준 메시지 채널 수신
  chrome.runtime.onMessage.addListener(thHandleMessage);

  // 2. DOM CustomEvent 및 글로벌 디스패처 (Orphaned 탭 / executeScript 폴백 수신)
  window.__TH_DISPATCH__ = thHandleMessage;
  window.addEventListener("TH_MESSAGE", (ev) => {
    if (ev && ev.detail) thHandleMessage(ev.detail);
  });
  thStart();
})();
