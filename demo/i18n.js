// Store language (FeastFleet is a fictional brand). Texts come from i18n.json, keyed by the English text; a text
// missing there stays English. The chosen language is remembered in this browser (localStorage), else the browser's
// language is used. Arabic switches the page to right-to-left.
"use strict";
window.FF_I18N = (() => {
  const LANGS = [["en-US", "English"], ["es-ES", "Español"], ["de-DE", "Deutsch"], ["fr-FR", "Français"],
    ["ja-JP", "日本語"], ["hi-IN", "हिन्दी"], ["ar-SA", "العربية"], ["sw-KE", "Kiswahili"], ["am-ET", "አማርኛ"], ["ta-IN", "தமிழ்"]];
  const KEY = "feastfleet-lang";
  let strings = {};

  function pick() {
    try { const saved = localStorage.getItem(KEY); if (LANGS.some(([c]) => c === saved)) return saved; } catch { /* storage off */ }
    for (const pref of navigator.languages || [navigator.language || ""]) {
      const match = LANGS.find(([c]) => c.split("-")[0] === pref.split("-")[0].toLowerCase());
      if (match) return match[0];
    }
    return "en-US";
  }
  let current = pick();

  // t("Order {id}", {id: "FF-2001"}) -> the text in the store language (or `lang`), placeholders filled in.
  function t(text, vars = {}, lang = current) {
    const out = (lang !== "en-US" && strings[text]?.[lang]) || text;
    return out.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m));
  }

  // Static page texts: data-i18n="English" for text, data-i18n-attr="attr=English;attr2=English" for attributes.
  function apply() {
    document.documentElement.lang = current.split("-")[0];
    document.documentElement.dir = current === "ar-SA" ? "rtl" : "ltr";
    for (const el of document.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
    for (const el of document.querySelectorAll("[data-i18n-attr]")) {
      for (const pair of el.dataset.i18nAttr.split(";")) {
        const [attr, text] = pair.split("=");
        el.setAttribute(attr, t(text));
      }
    }
    const select = document.getElementById("site-lang");
    if (select) select.value = current;
  }

  function set(lang) {
    current = lang;
    try { localStorage.setItem(KEY, lang); } catch { /* storage off: the choice lasts for this page only */ }
    apply();
    window.dispatchEvent(new CustomEvent("feastfleet:lang", { detail: lang }));
  }

  const select = document.getElementById("site-lang");
  if (select) {
    select.append(...LANGS.map(([value, label]) => new Option(label, value)));
    select.addEventListener("change", () => set(select.value));
  }
  const ready = fetch("i18n.json").then((r) => r.json()).then((d) => { strings = d.strings || {}; })
    .catch(() => { /* texts stay English */ }).then(apply);

  return { LANGS, ready, t, set, lang: () => current };
})();
