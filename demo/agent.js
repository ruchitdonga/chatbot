// FeastFleet support inbox (fictional brand): agents read chats the assistant handed off and reply to them.
// Talks to the orders API (/api/handoffs). Polls every few seconds; nothing is stored in the browser.
"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const LANG = { auto: "Language not chosen", "en-US": "English", "es-ES": "Español", "de-DE": "Deutsch",
                 "fr-FR": "Français", "ja-JP": "日本語", "hi-IN": "हिन्दी", "ar-SA": "العربية", "sw-KE": "Kiswahili",
                 "am-ET": "አማርኛ", "ta-IN": "தமிழ்" };
  const WHO = { customer: "Customer", bot: "Assistant", agent: "You" };
  let current = null, next = 0, rows = [];

  function minutesAgo(iso) {
    const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
    return m < 1 ? "just now" : `${m} min ago`;
  }

  async function refreshInbox() {
    try { rows = await fetch("/api/handoffs").then((r) => r.json()); } catch { return; }
    const list = $("inbox");
    if (!rows.length) {
      const li = document.createElement("li");
      li.className = "inbox-empty muted";
      li.textContent = "No customers waiting.";
      list.replaceChildren(li);
      return;
    }
    list.replaceChildren(...rows.map((r) => {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.className = "inbox-item";
      if (r.id === current) b.setAttribute("aria-current", "true");
      const top = document.createElement("span");
      top.className = "inbox-top";
      const lang = document.createElement("strong");
      lang.textContent = LANG[r.language] || r.language;
      const age = document.createElement("span");
      age.className = "muted small";
      age.textContent = `opened ${minutesAgo(r.opened_at)}`;
      top.append(lang, age);
      const last = document.createElement("span");
      last.className = "inbox-last";
      last.dir = "auto";
      last.textContent = r.last || "(no messages yet)";
      b.append(top, last);
      if (r.waiting) {
        const badge = document.createElement("span");
        badge.className = "waiting";
        badge.textContent = "Needs reply";
        b.append(badge);
      }
      b.addEventListener("click", () => open(r.id));
      li.append(b);
      return li;
    }));
  }

  function open(id) {
    current = id;
    next = 0;
    $("thread").replaceChildren();
    $("convo-empty").hidden = true;
    $("convo").hidden = false;
    const row = rows.find((r) => r.id === id);
    $("convo-title").textContent = `Chat …${id.slice(-6)}`;
    $("convo-meta").textContent = row ? `${LANG[row.language] || row.language} · opened ${minutesAgo(row.opened_at)}` : "";
    load();
    refreshInbox();
    $("reply-input").focus();
  }

  function line(m) {
    const el = document.createElement("div");
    el.className = `line from-${m.sender}`;
    const who = document.createElement("span");
    who.className = "who";
    who.textContent = WHO[m.sender] || m.sender;
    const text = document.createElement("p");
    text.dir = "auto";
    text.textContent = m.text;
    el.append(who, text);
    return el;
  }

  async function load() {
    if (!current) return;
    const id = current;
    let data;
    try {
      const res = await fetch(`/api/handoffs/${encodeURIComponent(id)}/messages?after=${next}`);
      if (!res.ok) return;
      data = await res.json();
    } catch { return; }
    if (id !== current) return;  // the agent switched chats while this was loading
    const thread = $("thread");
    thread.append(...data.messages.map(line));
    if (data.messages.length) thread.scrollTop = thread.scrollHeight;
    next = data.next;
    if (data.status === "closed") showClosed("This chat is closed.");
  }

  function showClosed(note) {
    current = null;
    $("convo").hidden = true;
    $("convo-empty").hidden = false;
    $("convo-empty").querySelector(".empty-title").textContent = note;
    refreshInbox();
  }

  $("reply").addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = $("reply-input").value.trim();
    if (!text || !current) return;
    $("reply-input").value = "";
    const res = await fetch(`/api/handoffs/${encodeURIComponent(current)}/messages`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender: "agent", text }) }).catch(() => null);
    if (!res || !res.ok) { $("reply-input").value = text; return; }  // keep the text so it can be resent
    load();
  });

  $("close-chat").addEventListener("click", async () => {
    if (!current) return;
    await fetch(`/api/handoffs/${encodeURIComponent(current)}/close`, { method: "POST" }).catch(() => {});
    showClosed("Chat closed. Its messages were deleted.");
  });

  refreshInbox();
  setInterval(refreshInbox, 3000);
  setInterval(load, 2000);
})();
