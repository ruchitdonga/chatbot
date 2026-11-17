// FeastFleet assistant widget. Talks to Rasa's REST channel through the nginx proxy (/webhooks/rest/webhook).
// Nothing is stored in the browser: a page reload starts a new conversation.
"use strict";
(() => {
  const LANGS = [
    ["", "Auto-detect"], ["en-US", "English"], ["es-ES", "Español"], ["de-DE", "Deutsch"], ["fr-FR", "Français"],
    ["ja-JP", "日本語"], ["hi-IN", "हिन्दी"], ["ar-SA", "العربية"], ["sw-KE", "Kiswahili"], ["am-ET", "አማርኛ"], ["ta-IN", "தமிழ்"],
  ];
  // Suggested phrases per language (AI-written, not yet reviewed by native speakers, like the assistant's replies).
  const CHIPS = {
    "en-US": ["I want to order a pizza", "Where is my order?", "My food arrived cold, I want a refund", "How much is delivery?"],
    "es-ES": ["Quiero pedir una pizza", "¿Dónde está mi pedido?", "La comida llegó fría y quiero un reembolso", "¿Cuánto cuesta la entrega?"],
    "de-DE": ["Ich möchte eine Pizza bestellen", "Wo ist meine Bestellung?", "Das Essen kam kalt an, ich will mein Geld zurück", "Was kostet die Lieferung?"],
    "fr-FR": ["Je veux commander une pizza", "Où est ma commande ?", "Le repas est arrivé froid, je veux être remboursé", "Combien coûte la livraison ?"],
    "ja-JP": ["ピザを注文したい", "注文はどこですか", "料理が冷めていたので返金してほしい", "配達料はいくらですか"],
    "hi-IN": ["मुझे पिज़्ज़ा ऑर्डर करना है", "मेरा ऑर्डर कहाँ है", "खाना ठंडा आया और मुझे पैसे वापस चाहिए", "डिलीवरी चार्ज कितना है?"],
    "ar-SA": ["أريد أن أطلب بيتزا", "أين طلبي", "وصل الطعام باردًا وأريد استرداد أموالي", "كم رسوم التوصيل؟"],
    "sw-KE": ["Nataka kuagiza pizza", "Oda yangu iko wapi", "Chakula kilifika kikiwa baridi, nataka kurudishiwa pesa", "Ada ya kuleta ni kiasi gani?"],
    "am-ET": ["ፒዛ ማዘዝ እፈልጋለሁ", "ትዕዛዜ የት ደረሰ", "ምግቡ ቀዝቅዞ ደረሰ ገንዘቤ ይመለስልኝ", "የማድረሻ ክፍያ ስንት ነው?"],
    "ta-IN": ["எனக்கு பிட்சா ஆர்டர் செய்ய வேண்டும்", "என் ஆர்டர் எங்கே இருக்கிறது", "உணவு குளிர்ந்து வந்தது, எனக்கு பணம் திரும்ப வேண்டும்", "டெலிவரி கட்டணம் எவ்வளவு?"],
  };

  const $ = (id) => document.getElementById(id);
  const chat = $("chat"), launcher = $("chat-launcher"), messages = $("messages"), input = $("input");
  const langSelect = $("lang"), chips = $("chips"), composer = $("composer"), sendBtn = composer.querySelector(".send");
  let sender = newSender();
  let busy = false;
  let agent = null;  // {id, next, timer} while a person has the chat (orders API /api/handoffs)
  const sub = chat.querySelector(".chat-sub");

  function newSender() { return "web-" + crypto.randomUUID(); }

  function openChat(prefill = "") {
    chat.hidden = false;
    launcher.setAttribute("aria-expanded", "true");
    if (prefill) input.value = prefill;
    input.focus();
  }
  function closeChat() {
    chat.hidden = true;
    launcher.setAttribute("aria-expanded", "false");
    launcher.focus();
  }

  function scrollDown() { messages.scrollTop = messages.scrollHeight; }

  function bubble(kind, text) {
    $("empty")?.remove();
    const el = document.createElement("div");
    el.className = `msg ${kind}`;
    el.dir = "auto";  // right-to-left for Arabic, per message
    el.textContent = text;
    messages.append(el);
    scrollDown();
  }

  function quickReplies(buttons) {
    const row = document.createElement("div");
    row.className = "quick";
    for (const b of buttons) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = b.title;
      btn.addEventListener("click", () => {
        row.querySelectorAll("button").forEach((x) => (x.disabled = true));
        send(b.payload, b.title);
      });
      row.append(btn);
    }
    messages.append(row);
    scrollDown();
  }

  // The assistant matched a dish to the menu: put it in the page's cart (app.js) and offer checkout.
  function addedToCart(item) {
    window.dispatchEvent(new CustomEvent("feastfleet:cart-add", { detail: item }));
    const link = document.createElement("a");
    link.className = "chat-checkout";
    link.href = "#/checkout";
    link.textContent = "View cart and check out";
    link.addEventListener("click", () => { if (window.matchMedia("(max-width: 640px)").matches) closeChat(); });
    messages.append(link);
    scrollDown();
  }

  function renderChips() {
    chips.replaceChildren(...(CHIPS[langSelect.value] || CHIPS["en-US"]).map((text) => {
      const b = document.createElement("button");
      b.type = "button";
      b.dir = "auto";
      b.textContent = text;
      b.addEventListener("click", () => send(text));
      return b;
    }));
  }

  function restart(note) {
    if (agent) closeHandoff();
    sender = newSender();
    messages.replaceChildren();
    if (note) bubble("system", note);
  }

  // ---- Human handoff: the assistant handed off, so the chat now goes to a person in the agent inbox ----
  function transcript() {
    return [...messages.querySelectorAll(".msg.user, .msg.bot")].slice(-50)
      .map((el) => ({ sender: el.classList.contains("user") ? "customer" : "bot", text: el.textContent.slice(0, 1000) }));
  }

  function setAgentMode(on) {
    sub.lastChild.textContent = on ? " Waiting for a person" : " AI assistant, not a person";  // poll() flips to Connected
    chat.classList.toggle("with-agent", on);
    chips.hidden = on;
    input.placeholder = on ? "Message the agent…" : "Type a message…";
  }

  async function startAgent() {
    try {
      const res = await fetch("/api/handoffs", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: sender, language: langSelect.value || "auto", transcript: transcript() }) });
      if (!res.ok) throw new Error(res.status === 503 ? "busy" : `HTTP ${res.status}`);
      const { id } = await res.json();
      agent = { id, next: transcript().length, timer: setInterval(poll, 2000) };
      setAgentMode(true);
      bubble("system", "You're now in the queue for a person. Write here and an agent will reply in this chat.");
    } catch (err) {
      bubble("system", err.message === "busy" ? "All agents are busy right now. Please try again shortly."
                                             : "We couldn't reach an agent right now. Please try again shortly.");
    }
  }

  async function poll() {
    if (!agent) return;
    try {
      const res = await fetch(`/api/handoffs/${encodeURIComponent(agent.id)}/messages?after=${agent.next}`);
      if (!res.ok) return;
      const data = await res.json();
      for (const m of data.messages) if (m.sender === "agent") {
        bubble("agent", m.text);
        sub.lastChild.textContent = " Connected to a person";
      }
      agent.next = data.next;
      if (data.status === "closed") endAgent("The agent closed this chat. You're back with the AI assistant.");
    } catch { /* network blip: try again on the next tick */ }
  }

  async function sendToAgent(text) {
    bubble("user", text);
    const res = await fetch(`/api/handoffs/${encodeURIComponent(agent.id)}/messages`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender: "customer", text: text.slice(0, 1000) }) }).catch(() => null);
    if (!res || !res.ok) bubble("system", "Your message didn't reach the agent. Please try again.");
  }

  function endAgent(note) {
    clearInterval(agent.timer);
    agent = null;
    setAgentMode(false);
    sender = newSender();  // the assistant starts a fresh conversation
    bubble("system", note);
  }

  function closeHandoff() {
    fetch(`/api/handoffs/${encodeURIComponent(agent.id)}/close`, { method: "POST" }).catch(() => {});
    clearInterval(agent.timer);
    agent = null;
    setAgentMode(false);
  }

  async function send(message, shown = message) {
    if (busy || !message.trim()) return;
    if (agent) return sendToAgent(message);
    busy = true;
    sendBtn.disabled = true;
    bubble("user", shown);
    const typing = document.createElement("div");
    typing.className = "typing";
    typing.setAttribute("aria-label", "Assistant is typing");
    typing.append(document.createElement("span"), document.createElement("span"), document.createElement("span"));
    messages.append(typing);
    scrollDown();
    try {
      const body = { sender, message };
      if (langSelect.value) body.metadata = { language: langSelect.value };
      const res = await fetch("/webhooks/rest/webhook", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      typing.remove();
      let handoff = false;
      for (const reply of await res.json()) {
        if (reply.text) bubble("bot", reply.text);
        if (reply.buttons?.length) quickReplies(reply.buttons);
        if (reply.custom?.cart_add) addedToCart(reply.custom.cart_add);
        if (reply.custom?.handoff) handoff = true;
      }
      if (handoff) await startAgent();
    } catch (err) {
      typing.remove();
      bubble("system", "The assistant is unavailable right now. Please try again in a moment.");
      console.error(err);
    } finally {
      busy = false;
      sendBtn.disabled = false;
    }
  }

  langSelect.append(...LANGS.map(([value, label]) => new Option(label, value)));
  langSelect.addEventListener("change", () => {
    renderChips();
    // The assistant keeps the first language of a conversation, so a new language means a new conversation.
    if (messages.querySelector(".msg")) restart(`New conversation: ${langSelect.selectedOptions[0].text}`);
  });
  renderChips();

  launcher.addEventListener("click", () => openChat());
  $("close").addEventListener("click", closeChat);
  $("restart").addEventListener("click", () => restart("New conversation"));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !chat.hidden) closeChat(); });
  composer.addEventListener("submit", (e) => {
    e.preventDefault();
    if (busy) return;  // keep the typed text until the previous reply arrives
    const text = input.value;
    input.value = "";
    send(text);
  });
  document.addEventListener("click", (e) => {
    const opener = e.target.closest("[data-open-chat]");
    if (opener) openChat(opener.dataset.openChat || "");
  });
})();
