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
  // The widget's own texts (AI-written, not yet reviewed by native speakers). Keys, in order:
  // ai, wait, agent, queue, busy, unreachable, closed, notSent, down, checkout, type, toAgent, fresh, empty.
  const KEYS = ["ai", "wait", "agent", "queue", "busy", "unreachable", "closed", "notSent", "down", "checkout", "type", "toAgent", "fresh", "empty"];
  const UI = Object.fromEntries(Object.entries({
    "en-US": ["AI assistant, not a person", "Waiting for a person", "Connected to a person", "You're now in the queue for a person. Write here and an agent will reply in this chat.", "All agents are busy right now. Please try again shortly.", "We couldn't reach an agent right now. Please try again shortly.", "The agent closed this chat. You're back with the AI assistant.", "Your message didn't reach the agent. Please try again.", "The assistant is unavailable right now. Please try again in a moment.", "View cart and check out", "Type a message…", "Message the agent…", "New conversation", "Order food, track an order or get help, in any of ten languages."],
    "es-ES": ["Asistente de IA, no una persona", "Esperando a una persona", "Conectado con una persona", "Estás en la cola para hablar con una persona. Escribe aquí y un agente te responderá en este chat.", "Todos los agentes están ocupados. Inténtalo de nuevo en un momento.", "No hemos podido contactar con un agente. Inténtalo de nuevo en un momento.", "El agente cerró este chat. Vuelves a hablar con el asistente de IA.", "Tu mensaje no llegó al agente. Inténtalo de nuevo.", "El asistente no está disponible ahora. Inténtalo de nuevo en un momento.", "Ver carrito y pagar", "Escribe un mensaje…", "Escribe al agente…", "Nueva conversación", "Pide comida, sigue un pedido u obtén ayuda en cualquiera de diez idiomas."],
    "de-DE": ["KI-Assistent, kein Mensch", "Warten auf eine Person", "Mit einer Person verbunden", "Sie sind jetzt in der Warteschlange für eine Person. Schreiben Sie hier, ein Mitarbeiter antwortet in diesem Chat.", "Alle Mitarbeiter sind gerade beschäftigt. Bitte versuchen Sie es gleich noch einmal.", "Wir konnten gerade keinen Mitarbeiter erreichen. Bitte versuchen Sie es gleich noch einmal.", "Der Mitarbeiter hat den Chat beendet. Sie sprechen wieder mit dem KI-Assistenten.", "Ihre Nachricht hat den Mitarbeiter nicht erreicht. Bitte versuchen Sie es noch einmal.", "Der Assistent ist gerade nicht erreichbar. Bitte versuchen Sie es gleich noch einmal.", "Warenkorb ansehen und bezahlen", "Nachricht schreiben…", "Nachricht an den Mitarbeiter…", "Neues Gespräch", "Essen bestellen, eine Bestellung verfolgen oder Hilfe bekommen, in zehn Sprachen."],
    "fr-FR": ["Assistant IA, pas une personne", "En attente d'une personne", "En contact avec une personne", "Vous êtes dans la file d'attente pour une personne. Écrivez ici, un conseiller vous répondra dans ce chat.", "Tous les conseillers sont occupés. Réessayez dans un instant.", "Impossible de joindre un conseiller pour le moment. Réessayez dans un instant.", "Le conseiller a fermé ce chat. Vous êtes de nouveau avec l'assistant IA.", "Votre message n'est pas parvenu au conseiller. Réessayez.", "L'assistant n'est pas disponible pour le moment. Réessayez dans un instant.", "Voir le panier et payer", "Écrivez un message…", "Écrire au conseiller…", "Nouvelle conversation", "Commandez, suivez une commande ou obtenez de l'aide, dans dix langues."],
    "ja-JP": ["AIアシスタント（人間ではありません）", "担当者を待っています", "担当者につながりました", "担当者の順番待ちに入りました。ここに書き込むと、担当者がこのチャットで返信します。", "ただいま担当者が全員対応中です。しばらくしてからもう一度お試しください。", "担当者に接続できませんでした。しばらくしてからもう一度お試しください。", "担当者がこのチャットを終了しました。AIアシスタントに戻ります。", "メッセージが担当者に届きませんでした。もう一度お試しください。", "アシスタントは現在ご利用いただけません。しばらくしてからもう一度お試しください。", "カートを見て注文する", "メッセージを入力…", "担当者へのメッセージ…", "新しい会話", "料理の注文、注文の確認、お問い合わせを10の言語で。"],
    "hi-IN": ["एआई सहायक, इंसान नहीं", "किसी व्यक्ति का इंतज़ार", "एक व्यक्ति से जुड़े हैं", "आप किसी व्यक्ति से बात करने की कतार में हैं। यहाँ लिखें, एक एजेंट इसी चैट में जवाब देगा।", "अभी सभी एजेंट व्यस्त हैं। कृपया थोड़ी देर में फिर कोशिश करें।", "अभी किसी एजेंट से संपर्क नहीं हो सका। कृपया थोड़ी देर में फिर कोशिश करें।", "एजेंट ने यह चैट बंद कर दी। अब आप फिर से एआई सहायक से बात कर रहे हैं।", "आपका संदेश एजेंट तक नहीं पहुँचा। कृपया फिर कोशिश करें।", "सहायक अभी उपलब्ध नहीं है। कृपया थोड़ी देर में फिर कोशिश करें।", "कार्ट देखें और चेकआउट करें", "संदेश लिखें…", "एजेंट को संदेश…", "नई बातचीत", "खाना ऑर्डर करें, ऑर्डर ट्रैक करें या मदद लें, दस भाषाओं में।"],
    "ar-SA": ["مساعد ذكاء اصطناعي، ليس إنسانًا", "في انتظار موظف", "متصل بموظف", "أنت الآن في قائمة الانتظار للتحدث مع موظف. اكتب هنا وسيرد عليك موظف في هذه المحادثة.", "جميع الموظفين مشغولون الآن. يرجى المحاولة بعد قليل.", "تعذّر الوصول إلى موظف الآن. يرجى المحاولة بعد قليل.", "أنهى الموظف هذه المحادثة. عدت الآن إلى مساعد الذكاء الاصطناعي.", "لم تصل رسالتك إلى الموظف. يرجى المحاولة مرة أخرى.", "المساعد غير متاح الآن. يرجى المحاولة بعد قليل.", "عرض السلة وإتمام الطلب", "اكتب رسالة…", "اكتب رسالة إلى الموظف…", "محادثة جديدة", "اطلب الطعام أو تتبّع طلبك أو احصل على المساعدة بعشر لغات."],
    "sw-KE": ["Msaidizi wa AI, si binadamu", "Unasubiri mtu", "Umeunganishwa na mtu", "Sasa uko kwenye foleni ya kuongea na mtu. Andika hapa na wakala atakujibu kwenye gumzo hili.", "Mawakala wote wana shughuli sasa. Tafadhali jaribu tena baada ya muda mfupi.", "Hatukuweza kumpata wakala sasa. Tafadhali jaribu tena baada ya muda mfupi.", "Wakala amefunga gumzo hili. Umerudi kwa msaidizi wa AI.", "Ujumbe wako haukumfikia wakala. Tafadhali jaribu tena.", "Msaidizi hapatikani sasa. Tafadhali jaribu tena baada ya muda mfupi.", "Angalia kikapu na ulipe", "Andika ujumbe…", "Mwandikie wakala…", "Mazungumzo mapya", "Agiza chakula, fuatilia oda au pata msaada, kwa lugha kumi."],
    "am-ET": ["የAI ረዳት፣ ሰው አይደለም", "ሰው በመጠባበቅ ላይ", "ከሰው ጋር ተገናኝተዋል", "አሁን ከሰው ጋር ለመነጋገር ወረፋ ላይ ነዎት። እዚህ ይጻፉ፤ ወኪል በዚህ ውይይት ይመልስልዎታል።", "ሁሉም ወኪሎች አሁን ሥራ ላይ ናቸው። እባክዎ ትንሽ ቆይተው እንደገና ይሞክሩ።", "አሁን ወኪል ማግኘት አልቻልንም። እባክዎ ትንሽ ቆይተው እንደገና ይሞክሩ።", "ወኪሉ ይህን ውይይት ዘግቷል። ወደ AI ረዳቱ ተመልሰዋል።", "መልዕክትዎ ወኪሉ ጋር አልደረሰም። እባክዎ እንደገና ይሞክሩ።", "ረዳቱ አሁን አይገኝም። እባክዎ ትንሽ ቆይተው እንደገና ይሞክሩ።", "ጋሪውን ይመልከቱ እና ይክፈሉ", "መልዕክት ይጻፉ…", "ለወኪሉ ይጻፉ…", "አዲስ ውይይት", "ምግብ ይዘዙ፣ ትዕዛዝ ይከታተሉ ወይም እርዳታ ያግኙ፣ በአስር ቋንቋዎች።"],
    "ta-IN": ["AI உதவியாளர், மனிதர் அல்ல", "ஒரு நபருக்காகக் காத்திருக்கிறது", "ஒரு நபருடன் இணைக்கப்பட்டுள்ளீர்கள்", "ஒரு நபருடன் பேச நீங்கள் வரிசையில் உள்ளீர்கள். இங்கே எழுதுங்கள், ஒரு முகவர் இந்த அரட்டையில் பதிலளிப்பார்.", "எல்லா முகவர்களும் இப்போது பணியில் உள்ளனர். சிறிது நேரத்தில் மீண்டும் முயற்சிக்கவும்.", "இப்போது ஒரு முகவரைத் தொடர்பு கொள்ள முடியவில்லை. சிறிது நேரத்தில் மீண்டும் முயற்சிக்கவும்.", "முகவர் இந்த அரட்டையை முடித்துவிட்டார். நீங்கள் மீண்டும் AI உதவியாளருடன் இருக்கிறீர்கள்.", "உங்கள் செய்தி முகவரைச் சென்றடையவில்லை. மீண்டும் முயற்சிக்கவும்.", "உதவியாளர் இப்போது கிடைக்கவில்லை. சிறிது நேரத்தில் மீண்டும் முயற்சிக்கவும்.", "கார்ட்டைப் பார்த்து செக்அவுட் செய்யவும்", "ஒரு செய்தியை எழுதுங்கள்…", "முகவருக்கு எழுதுங்கள்…", "புதிய உரையாடல்", "உணவை ஆர்டர் செய்யுங்கள், ஆர்டரைக் கண்காணியுங்கள் அல்லது உதவி பெறுங்கள், பத்து மொழிகளில்."],
  }).map(([lang, texts]) => [lang, Object.fromEntries(KEYS.map((k, i) => [k, texts[i]]))]));

  const $ = (id) => document.getElementById(id);
  const chat = $("chat"), launcher = $("chat-launcher"), messages = $("messages"), input = $("input");
  const langSelect = $("lang"), chips = $("chips"), composer = $("composer"), sendBtn = composer.querySelector(".send");
  let sender = newSender();
  let busy = false;
  let agent = null;  // {id, next, timer, connected} while a person has the chat (orders API /api/handoffs)
  let convLang = null;  // the conversation's language, from the assistant's first reply (custom.lang) in Auto-detect
  const sub = chat.querySelector(".chat-sub");
  const lang = () => langSelect.value || convLang || "en-US";
  const ui = (key) => (UI[lang()] || UI["en-US"])[key];

  // Status line, placeholder and suggestions in the conversation's language.
  function refreshUi() {
    sub.lastChild.textContent = " " + ui(!agent ? "ai" : agent.connected ? "agent" : "wait");
    input.placeholder = ui(agent ? "toAgent" : "type");
    const empty = $("empty");
    if (empty) empty.textContent = ui("empty");
    renderChips();
  }

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
    if (messages.lastElementChild?.classList.contains("chat-checkout")) return;  // one link for several dishes
    const link = document.createElement("a");
    link.className = "chat-checkout";
    link.href = "#/checkout";
    link.textContent = ui("checkout");
    link.addEventListener("click", () => { if (window.matchMedia("(max-width: 640px)").matches) closeChat(); });
    messages.append(link);
    scrollDown();
  }

  function renderChips() {
    chips.replaceChildren(...(CHIPS[lang()] || CHIPS["en-US"]).map((text) => {
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
    convLang = null;  // a new conversation detects its language again
    messages.replaceChildren();
    if (note) bubble("system", note);
    refreshUi();
  }

  // ---- Human handoff: the assistant handed off, so the chat now goes to a person in the agent inbox ----
  function transcript() {
    return [...messages.querySelectorAll(".msg.user, .msg.bot")].slice(-50)
      .map((el) => ({ sender: el.classList.contains("user") ? "customer" : "bot", text: el.textContent.slice(0, 1000) }));
  }

  function setAgentMode(on) {
    chat.classList.toggle("with-agent", on);
    chips.hidden = on;
    refreshUi();  // status: waiting for a person, then connected once the agent replies (poll)
  }

  async function startAgent() {
    try {
      const res = await fetch("/api/handoffs", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: sender, language: langSelect.value || convLang || "auto", transcript: transcript() }) });
      if (!res.ok) throw new Error(res.status === 503 ? "busy" : `HTTP ${res.status}`);
      const { id } = await res.json();
      agent = { id, next: transcript().length, timer: setInterval(poll, 2000), connected: false };
      setAgentMode(true);
      bubble("system", ui("queue"));
    } catch (err) {
      bubble("system", ui(err.message === "busy" ? "busy" : "unreachable"));
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
        agent.connected = true;
        refreshUi();
      }
      agent.next = data.next;
      if (data.status === "closed") endAgent(ui("closed"));
    } catch { /* network blip: try again on the next tick */ }
  }

  async function sendToAgent(text) {
    bubble("user", text);
    const res = await fetch(`/api/handoffs/${encodeURIComponent(agent.id)}/messages`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender: "customer", text: text.slice(0, 1000) }) }).catch(() => null);
    if (!res || !res.ok) bubble("system", ui("notSent"));
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
        if (reply.custom?.lang && !convLang) { convLang = reply.custom.lang; refreshUi(); }  // detected language
        if (reply.text) bubble("bot", reply.text);
        if (reply.buttons?.length) quickReplies(reply.buttons);
        if (reply.custom?.cart_add) addedToCart(reply.custom.cart_add);
        if (reply.custom?.handoff) handoff = true;
      }
      if (handoff) await startAgent();
    } catch (err) {
      typing.remove();
      bubble("system", ui("down"));
      console.error(err);
    } finally {
      busy = false;
      sendBtn.disabled = false;
    }
  }

  langSelect.append(...LANGS.map(([value, label]) => new Option(label, value)));
  langSelect.addEventListener("change", () => {
    // The assistant keeps the first language of a conversation, so a new language means a new conversation.
    if (messages.querySelector(".msg")) restart(`${ui("fresh")}: ${langSelect.selectedOptions[0].text}`);
    else refreshUi();
  });
  refreshUi();

  launcher.addEventListener("click", () => openChat());
  $("close").addEventListener("click", closeChat);
  $("restart").addEventListener("click", () => restart(ui("fresh")));
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
