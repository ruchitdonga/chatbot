// FeastFleet demo chat (fictional business). Talks to Rasa's REST channel through the nginx proxy (/webhooks/...).
// Nothing is stored in the browser: a page reload starts a new conversation.
"use strict";

const LANGS = [
  ["", "Auto-detect"], ["en-US", "English"], ["es-ES", "Español"], ["de-DE", "Deutsch"], ["fr-FR", "Français"],
  ["ja-JP", "日本語"], ["hi-IN", "हिन्दी"], ["ar-SA", "العربية"], ["sw-KE", "Kiswahili"], ["am-ET", "አማርኛ"], ["ta-IN", "தமிழ்"],
];

// Suggestion chips and the menu-card order sentence per language (AI-written, unreviewed, like the bot replies).
const PHRASES = {
  "en-US": { order: "I want to order a {dish}", chips: ["I want to order a pizza", "Where is my order?", "My food arrived cold, I want a refund"] },
  "es-ES": { order: "Quiero pedir {dish}", chips: ["Quiero pedir una pizza", "¿Dónde está mi pedido?", "La comida llegó fría y quiero un reembolso"] },
  "de-DE": { order: "Ich möchte {dish} bestellen", chips: ["Ich möchte eine Pizza bestellen", "Wo ist meine Bestellung?", "Das Essen kam kalt an, ich will mein Geld zurück"] },
  "fr-FR": { order: "Je veux commander {dish}", chips: ["Je veux commander une pizza", "Où est ma commande ?", "Le repas est arrivé froid, je veux être remboursé"] },
  "ja-JP": { order: "{dish}を注文したい", chips: ["ピザを注文したい", "注文はどこですか", "料理が冷めていたので返金してほしい"] },
  "hi-IN": { order: "मुझे {dish} ऑर्डर करना है", chips: ["मुझे पिज़्ज़ा ऑर्डर करना है", "मेरा ऑर्डर कहाँ है", "खाना ठंडा आया और मुझे पैसे वापस चाहिए"] },
  "ar-SA": { order: "أريد أن أطلب {dish}", chips: ["أريد أن أطلب بيتزا", "أين طلبي", "وصل الطعام باردًا وأريد استرداد أموالي"] },
  "sw-KE": { order: "Nataka kuagiza {dish}", chips: ["Nataka kuagiza pizza", "Oda yangu iko wapi", "Chakula kilifika kikiwa baridi, nataka kurudishiwa pesa"] },
  "am-ET": { order: "{dish} ማዘዝ እፈልጋለሁ", chips: ["ፒዛ ማዘዝ እፈልጋለሁ", "ትዕዛዜ የት ደረሰ", "ምግቡ ቀዝቅዞ ደረሰ ገንዘቤ ይመለስልኝ"] },
  "ta-IN": { order: "எனக்கு {dish} ஆர்டர் செய்ய வேண்டும்", chips: ["எனக்கு பிட்சா ஆர்டர் செய்ய வேண்டும்", "என் ஆர்டர் எங்கே இருக்கிறது", "உணவு குளிர்ந்து வந்தது, எனக்கு பணம் திரும்ப வேண்டும்"] },
};

const $ = (id) => document.getElementById(id);
const chat = $("chat"), launcher = $("chat-launcher"), messages = $("messages"), input = $("input");
const langSelect = $("lang"), chips = $("chips"), composer = $("composer");

let sender = newSender();
let busy = false;

function newSender() { return "web-" + crypto.randomUUID(); }
function phrases() { return PHRASES[langSelect.value] || PHRASES["en-US"]; }

function openChat(focus = true) {
  chat.hidden = false;
  launcher.setAttribute("aria-expanded", "true");
  if (focus) input.focus();
}
function closeChat() {
  chat.hidden = true;
  launcher.setAttribute("aria-expanded", "false");
  launcher.focus();
}

function bubble(kind, text) {
  $("empty")?.remove();
  const el = document.createElement("div");
  el.className = `msg ${kind}`;
  el.dir = "auto";  // right-to-left for Arabic, per message
  el.textContent = text;
  messages.append(el);
  messages.scrollTop = messages.scrollHeight;
  return el;
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
  messages.scrollTop = messages.scrollHeight;
}

function renderChips() {
  chips.replaceChildren(...phrases().chips.map((text) => {
    const b = document.createElement("button");
    b.type = "button";
    b.dir = "auto";
    b.textContent = text;
    b.addEventListener("click", () => send(text));
    return b;
  }));
}

function restart(note) {
  sender = newSender();
  messages.replaceChildren();
  if (note) bubble("system", note);
}

async function send(message, shown = message) {
  if (busy || !message.trim()) return;
  busy = true;
  composer.querySelector(".send").disabled = true;
  bubble("user", shown);
  const typing = document.createElement("div");
  typing.className = "typing";
  typing.setAttribute("aria-label", "Assistant is typing");
  typing.append(document.createElement("span"), document.createElement("span"), document.createElement("span"));
  messages.append(typing);
  messages.scrollTop = messages.scrollHeight;
  try {
    const body = { sender, message };
    if (langSelect.value) body.metadata = { language: langSelect.value };
    const res = await fetch("/webhooks/rest/webhook", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    typing.remove();
    for (const reply of await res.json()) {
      if (reply.text) bubble("bot", reply.text);
      if (reply.buttons?.length) quickReplies(reply.buttons);
    }
  } catch (err) {
    typing.remove();
    bubble("system", "The assistant is unavailable right now. Please try again in a moment.");
    console.error(err);
  } finally {
    busy = false;
    composer.querySelector(".send").disabled = false;
  }
}

// Wiring
langSelect.append(...LANGS.map(([value, label]) => new Option(label, value)));
langSelect.addEventListener("change", () => {
  renderChips();
  // The bot keeps the first language of a conversation, so a new language means a new conversation.
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

document.querySelectorAll("[data-open-chat]").forEach((el) => el.addEventListener("click", () => {
  openChat();
  const [order, track] = phrases().chips;
  input.value = { order, track }[el.dataset.openChat] ?? "";  // "help" just opens the chat
}));

document.querySelectorAll("[data-dish]").forEach((el) => el.addEventListener("click", () => {
  openChat(false);
  send(phrases().order.replace("{dish}", el.dataset.dish));
}));
