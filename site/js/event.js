/**
 * WOOOLY ANJO イベント一覧
 * data/events.json を読み込んで表示
 */
(function () {
  "use strict";

  const list = document.getElementById("event-list");
  const sortButtons = document.querySelectorAll(".sort-button");
  if (!list) return;

  let events = [];
  let currentSort = "desc";

  function escapeHTML(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatDateJP(dateString) {
    const parts = String(dateString).split("-");
    if (parts.length !== 3) return escapeHTML(dateString);
    const date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    const days = ["日", "月", "火", "水", "木", "金", "土"];
    return `${parts[0]}年${Number(parts[1])}月${Number(parts[2])}日（${days[date.getDay()]}）`;
  }

  function eventDateValue(event) {
    const time = event.start || "00:00";
    return new Date(`${event.date}T${time}:00`);
  }

  function isPastEvent(event) {
    if (!event.date) return false;
    const endTime = event.end || "23:59";
    return new Date(`${event.date}T${endTime}:59`).getTime() < Date.now();
  }

  function timeText(event) {
    if (event.start && event.end) return `${event.start}〜${event.end}`;
    return event.start || event.end || "";
  }

  function render() {
    if (!events.length) {
      list.innerHTML = '<div class="event-empty">現在、掲載中のイベントはありません。</div>';
      return;
    }

    const sorted = [...events].sort((a, b) => {
      const diff = eventDateValue(a) - eventDateValue(b);
      return currentSort === "asc" ? diff : -diff;
    });

    list.innerHTML = "";

    sorted.forEach((event) => {
      const article = document.createElement("article");
      article.className = "event-item";
      const past = isPastEvent(event);
      if (past) article.classList.add("is-past");

      const venueQuery = event.address || event.venue || "";
      const mapUrl = venueQuery
        ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(venueQuery)}`
        : "";
      const eventUrl = /^https?:\/\//i.test(event.url || "") ? event.url : "";
      const time = timeText(event);

      article.innerHTML = `
        <div class="event-head">
          <div class="event-name">
            ${past ? '<span class="status-done">終了</span>' : ""}
            ${escapeHTML(event.name)}
          </div>
          <time class="event-date" datetime="${escapeHTML(event.date)}">
            ${formatDateJP(event.date)}
          </time>
        </div>
        <div class="event-detail">
          ${time ? `<p class="event-time"><strong>時間</strong> ${escapeHTML(time)}</p>` : ""}
          ${event.venue ? `<p class="event-venue"><strong>会場</strong> ${escapeHTML(event.venue)}</p>` : ""}
          ${event.address ? `<p class="event-address"><strong>住所</strong> ${escapeHTML(event.address)}</p>` : ""}
          ${event.note ? `<p class="event-note">${escapeHTML(event.note)}</p>` : ""}
          <div class="event-links">
            ${mapUrl ? `<a href="${mapUrl}" target="_blank" rel="noopener noreferrer">地図を見る →</a>` : ""}
            ${eventUrl ? `<a href="${escapeHTML(eventUrl)}" target="_blank" rel="noopener noreferrer">イベント詳細 →</a>` : ""}
          </div>
        </div>`;

      list.appendChild(article);
    });
  }

  async function loadEvents() {
    try {
      const response = await fetch(`data/events.json?v=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data)) throw new Error("events.json の形式が正しくありません");
      events = data;
      render();
    } catch (error) {
      console.error("イベント情報の読み込みに失敗しました:", error);
      list.innerHTML = '<div class="event-error">イベント情報を読み込めませんでした。<br>時間をおいて再度お試しください。</div>';
    }
  }

  sortButtons.forEach((button) => {
    button.addEventListener("click", () => {
      currentSort = button.dataset.sort === "asc" ? "asc" : "desc";
      sortButtons.forEach((item) => {
        const active = item === button;
        item.classList.toggle("active", active);
        item.setAttribute("aria-pressed", String(active));
      });
      render();
    });
  });

  loadEvents();
})();
