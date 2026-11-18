// FeastFleet storefront (FeastFleet is a fictional brand): menu, cart, checkout, order status and tracking.
// Orders go to the orders API (/api/..., src/shop/app.py). Card payments are simulated: the card number, expiry and
// CVC are checked here and never leave the page; only the brand and last four digits are sent.
"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const view = $("view");
  const money = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
  const fmt = (cents) => money.format(cents / 100);
  const t = (text, vars) => window.FF_I18N.t(text, vars);  // i18n.js: the store language
  const CART_KEY = "feastfleet-cart", LAST_ORDER_KEY = "feastfleet-last-order";
  const STEP_LABELS = { confirmed: "Order confirmed", preparing: "Preparing your food", on_the_way: "On the way",
                        delivered: "Delivered", ready: "Ready for pickup" };
  let menu = null, category = "All", query = "", pollTimer = null, fulfilment = "delivery", refreshCheckout = null;
  let cart = read(localStorage, CART_KEY) || {};

  // ---------- helpers ----------
  function h(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else if (k === "class") el.className = v;
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) if (c != null && c !== false) el.append(c.nodeType ? c : String(c));
    return el;
  }
  function read(store, key) { try { return JSON.parse(store.getItem(key)); } catch { return null; } }
  function write(store, key, value) { try { store.setItem(key, JSON.stringify(value)); } catch { /* storage off */ } }

  async function api(path, options = {}) {
    const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(typeof data.detail === "string" ? data.detail : t("Please check your details and try again."));
      err.status = res.status;
      throw err;
    }
    return data;
  }

  let toastTimer;
  function toast(text) {
    const t = $("toast");
    t.textContent = text;
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (t.hidden = true), 2200);
  }

  // ---------- cart ----------
  function lines() {
    return menu ? Object.entries(cart).map(([id, qty]) => ({ item: menu.byId[id], qty })).filter((l) => l.item) : [];
  }
  function sums(mode = fulfilment) {
    const subtotal = lines().reduce((s, l) => s + l.item.price * l.qty, 0);
    const fee = mode === "pickup" || subtotal === 0 || subtotal >= menu.free_delivery_from ? 0 : menu.delivery_fee;
    return { subtotal, fee, total: subtotal + fee };
  }
  function setQty(id, qty) {
    if (qty <= 0) delete cart[id]; else cart[id] = Math.min(qty, 20);
    write(localStorage, CART_KEY, cart);
    renderCart();
    // On checkout, update the totals without rebuilding the form (keeps what the customer typed).
    if (refreshCheckout && lines().length) refreshCheckout();
    else if (!location.hash.startsWith("#/order")) route(false);
  }
  function stepper(id, qty) {
    const name = menu.byId[id].name;
    return h("div", { class: "stepper" },
      h("button", { type: "button", "aria-label": t("Remove one {name}", { name }), onclick: () => setQty(id, qty - 1) }, "−"),
      h("span", { "aria-live": "polite" }, qty),
      h("button", { type: "button", "aria-label": t("Add one {name}", { name }), onclick: () => setQty(id, qty + 1) }, "+"));
  }

  function cartNodes() {
    const ls = lines();
    if (!ls.length) {
      return { body: [h("div", { class: "empty-cart" }, h("p", { class: "empty-title" }, t("Your cart is empty")),
        h("p", { class: "muted" }, t("Add dishes from the menu and they'll show up here.")))], foot: [] };
    }
    const s = sums("delivery");
    const more = menu.free_delivery_from - s.subtotal;
    return {
      body: ls.map(({ item, qty }) => h("div", { class: "cart-line" },
        h("span", { class: `diet ${item.veg ? "veg" : "nonveg"}`, role: "img", "aria-label": item.veg ? t("Vegetarian") : t("Non-vegetarian") }),
        h("div", { class: "cart-info" }, h("p", { class: "cart-name" }, item.name), h("p", { class: "muted" }, fmt(item.price * qty))),
        stepper(item.id, qty))),
      foot: [
        more > 0 ? h("p", { class: "free-hint" }, t("Add {amount} more for free delivery", { amount: fmt(more) })) : h("p", { class: "free-hint ok" }, t("Free delivery unlocked")),
        h("div", { class: "sum-row" }, h("span", {}, t("Item total")), h("span", {}, fmt(s.subtotal))),
        h("div", { class: "sum-row" }, h("span", {}, t("Delivery fee")), h("span", {}, s.fee ? fmt(s.fee) : t("Free"))),
        h("div", { class: "sum-row total" }, h("span", {}, t("To pay")), h("span", {}, fmt(s.total))),
        h("a", { class: "btn btn-primary block", href: "#/checkout", onclick: closeCart }, t("Checkout"))],
    };
  }

  function renderCart() {
    const count = Object.values(cart).reduce((a, b) => a + b, 0);
    $("cart-count").textContent = count;
    $("cart-count").hidden = count === 0;
    if (!menu) return;
    const fill = (body, foot) => { const c = cartNodes(); body.replaceChildren(...c.body); foot.replaceChildren(...c.foot); };
    fill($("cart-body"), $("cart-foot"));
    const side = $("cart-side");
    if (side) {
      const body = h("div", { class: "side-body" }), foot = h("div", { class: "side-foot" });
      fill(body, foot);
      side.replaceChildren(h("h2", {}, t("Your cart")), body, foot);
    }
    const bar = $("cart-bar");
    const page = (location.hash || "#/").split("/")[1] || "";
    bar.hidden = !count || page !== "";
    bar.replaceChildren(h("span", {}, count === 1 ? t("1 item · {total}", { total: fmt(sums("delivery").total) })
        : t("{count} items · {total}", { count, total: fmt(sums("delivery").total) })),
      h("strong", {}, t("View cart")));
  }
  function openCart() {
    $("cart").hidden = false; $("scrim").hidden = false;
    $("cart-btn").setAttribute("aria-expanded", "true");
    $("cart-close").focus();
  }
  function closeCart() {
    $("cart").hidden = true; $("scrim").hidden = true;
    $("cart-btn").setAttribute("aria-expanded", "false");
  }

  // ---------- pages ----------
  function dishRow(m) {
    const qty = cart[m.id];
    return h("li", { class: "dish" },
      h("div", { class: "dish-info" },
        h("span", { class: `diet ${m.veg ? "veg" : "nonveg"}`, role: "img", "aria-label": m.veg ? t("Vegetarian") : t("Non-vegetarian") }),
        h("h3", {}, m.name),
        h("p", { class: "dish-price" }, fmt(m.price)),
        h("p", { class: "dish-desc" }, t(m.desc))),
      h("div", { class: "dish-pic" },
        h("div", { class: "pic", "aria-hidden": "true" }, m.emoji),
        qty ? stepper(m.id, qty)
          : h("button", { class: "add", type: "button", "aria-label": t("Add {name} to cart", { name: m.name }),
                          onclick: () => { setQty(m.id, 1); toast(t("{name} added", { name: m.name })); } }, t("ADD"))));
  }

  function clearSearch() {
    query = "";
    $("search").value = "";
    route(false);
  }

  function renderHome() {
    const q = query.trim().toLowerCase();
    const cats = [...new Set(menu.items.map((m) => m.category))];
    const shown = menu.items.filter((m) => (category === "All" || m.category === category)
      && (!q || `${m.name} ${m.desc} ${t(m.desc)}`.toLowerCase().includes(q)));
    const groups = cats.map((c) => [c, shown.filter((m) => m.category === c)]).filter(([, list]) => list.length);
    view.replaceChildren(
      h("section", { class: "store wrap" },
        h("div", { class: "store-text" },
          h("h1", {}, "FeastFleet Kitchen"),
          h("p", { class: "muted" }, t("Biryani, South Indian, curries, street food, pizza, Japanese, Middle Eastern and East African")),
          h("ul", { class: "store-meta" },
            h("li", {}, h("strong", {}, t("30–35 min delivery"))),
            h("li", {}, t("Free delivery above {amount}", { amount: fmt(menu.free_delivery_from) })),
            h("li", {}, t("Card or cash on delivery")))),
        h("button", { class: "help-card", type: "button", "data-open-chat": "" },
          h("strong", {}, t("Questions about an order?")),
          h("span", {}, t("Ask our AI assistant in your language. It speaks ten, including हिन्दी, தமிழ், العربية and Kiswahili.")))),
      h("div", { class: "layout wrap" },
        h("div", { class: "menu-col" },
          h("nav", { class: "cats", "aria-label": t("Categories") }, ["All", ...cats].map((c) =>
            h("button", { type: "button", class: "cat", "aria-pressed": String(c === category),
                          onclick: () => { category = c; route(false); } }, t(c)))),
          groups.length
            ? groups.map(([c, list]) => h("section", { class: "menu-sec", "aria-label": t(c) },
                h("h2", {}, t(c), h("span", { class: "count" }, ` (${list.length})`)),
                h("ul", { class: "dishes" }, list.map(dishRow))))
            : h("div", { class: "no-results" },
                h("p", { class: "empty-title" }, t("No dishes match “{query}”", { query })),
                h("p", { class: "muted" }, t("Try another dish or clear the search.")),
                h("button", { class: "btn btn-ghost", type: "button", onclick: clearSearch }, t("Clear search")))),
        h("aside", { class: "cart-side", id: "cart-side", "aria-label": t("Your cart") })));
  }

  function field(label, input, hint) {
    const id = input.id;
    return h("div", { class: "field" }, h("label", { for: id }, label), input,
      hint ? h("p", { class: "hint-text" }, hint) : null, h("p", { class: "error", id: `${id}-error` }));
  }
  function radioCard(name, value, title, sub, checked, onchange) {
    return h("label", { class: "radio-card" },
      h("input", { type: "radio", name, value, checked, onchange }),
      h("span", {}, h("strong", {}, title), h("span", { class: "muted" }, sub)));
  }
  function luhn(num) {
    let sum = 0;
    for (let i = 0; i < num.length; i++) {
      let d = +num[num.length - 1 - i];
      if (i % 2) { d *= 2; if (d > 9) d -= 9; }
      sum += d;
    }
    return num.length >= 12 && sum % 10 === 0;
  }
  function brand(num) {
    return /^4/.test(num) ? "Visa" : /^(5[1-5]|2[2-7])/.test(num) ? "Mastercard" : /^3[47]/.test(num) ? "Amex" : "Card";
  }

  function renderCheckout() {
    if (!lines().length) {
      view.replaceChildren(h("section", { class: "wrap page narrow" }, h("h1", {}, t("Checkout")),
        h("p", {}, t("Your cart is empty.")), h("a", { class: "btn btn-primary", href: "#/" }, t("Browse the menu"))));
      return;
    }
    let payMethod = "card";
    const name = h("input", { id: "c-name", autocomplete: "name", maxlength: "80", required: true });
    const phone = h("input", { id: "c-phone", type: "tel", autocomplete: "tel", maxlength: "25", required: true, placeholder: "+91 98765 43210" });
    const address = h("textarea", { id: "c-address", autocomplete: "street-address", rows: "2", maxlength: "200" });
    const notes = h("input", { id: "c-notes", maxlength: "200", placeholder: t("Gate code, floor, allergies…") });
    // Card fields: autocomplete off so the browser neither fills in nor saves a real card here.
    const cardNo = h("input", { id: "p-number", inputmode: "numeric", autocomplete: "off", maxlength: "23", placeholder: "4242 4242 4242 4242" });
    const cardName = h("input", { id: "p-name", autocomplete: "off", maxlength: "60" });
    const expiry = h("input", { id: "p-expiry", inputmode: "numeric", autocomplete: "off", maxlength: "5", placeholder: "MM/YY" });
    const cvc = h("input", { id: "p-cvc", inputmode: "numeric", autocomplete: "off", maxlength: "4", placeholder: "123" });
    cardNo.addEventListener("input", () => {
      cardNo.value = cardNo.value.replace(/\D/g, "").slice(0, 19).replace(/(\d{4})(?=\d)/g, "$1 ");
    });
    expiry.addEventListener("input", () => {
      const d = expiry.value.replace(/\D/g, "").slice(0, 4);
      expiry.value = d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
    });
    cvc.addEventListener("input", () => (cvc.value = cvc.value.replace(/\D/g, "")));

    const addressField = field(t("Delivery address"), address);
    const cardPanel = h("div", { class: "card-panel" },
      h("p", { class: "test-mode" }, h("strong", {}, t("Test mode")),
        " ", t("Use 4242 4242 4242 4242 with any future date and any CVC (4000 0000 0000 0002 is declined). Card details stay on this page; only the last four digits are sent.")),
      field(t("Card number"), cardNo),
      field(t("Name on card"), cardName),
      h("div", { class: "two" }, field(t("Expiry"), expiry), field("CVC", cvc)));
    const codTitle = h("strong", {}, t("Cash on delivery"));
    const codSub = h("span", { class: "muted" }, t("Pay the rider when your food arrives"));
    const codCard = h("label", { class: "radio-card" },
      h("input", { type: "radio", name: "pay", value: "cod", onchange: () => setPay("cod") }), h("span", {}, codTitle, codSub));
    const payError = h("p", { class: "error", id: "pay-error", role: "alert" });
    const formError = h("p", { class: "error form-error", role: "alert" });
    const summary = h("div", { class: "summary-lines" });
    const placeBtn = h("button", { class: "btn btn-primary block", type: "submit" });

    function setPay(m) { payMethod = m; cardPanel.hidden = m !== "card"; payError.textContent = ""; }
    function setMode(m) {
      fulfilment = m;
      addressField.hidden = m !== "delivery";
      codTitle.textContent = m === "pickup" ? t("Pay at pickup") : t("Cash on delivery");
      codSub.textContent = m === "pickup" ? t("Pay in the shop when you collect") : t("Pay the rider when your food arrives");
      renderSummary();
    }
    function renderSummary() {
      const s = sums();
      summary.replaceChildren(...lines().map(({ item, qty }) =>
        h("div", { class: "sum-row" }, h("span", {}, `${qty} × ${item.name}`), h("span", {}, fmt(item.price * qty)))),
        h("hr"),
        h("div", { class: "sum-row" }, h("span", {}, t("Item total")), h("span", {}, fmt(s.subtotal))),
        h("div", { class: "sum-row" }, h("span", {}, fulfilment === "pickup" ? t("Pickup") : t("Delivery fee")), h("span", {}, s.fee ? fmt(s.fee) : t("Free"))),
        h("div", { class: "sum-row total" }, h("span", {}, t("To pay")), h("span", {}, fmt(s.total))));
      placeBtn.textContent = t("Place order · {total}", { total: fmt(s.total) });
    }
    function mark(input, message) {
      $(`${input.id}-error`).textContent = message || "";
      if (message) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid");
      return !message;
    }
    function validate() {
      const digits = cardNo.value.replace(/\D/g, "");
      const [mm, yy] = expiry.value.split("/").map(Number);
      const now = new Date(), expEnd = new Date(2000 + yy, mm, 1);
      const checks = [
        mark(name, name.value.trim() ? "" : t("Please enter your name.")),
        mark(phone, (phone.value.match(/\d/g) || []).length >= 7 && /^\+?[0-9 ()-]+$/.test(phone.value.trim()) ? "" : t("Please enter a valid phone number.")),
        mark(address, fulfilment === "pickup" || address.value.trim() ? "" : t("Please enter your delivery address.")),
      ];
      if (payMethod === "card") {
        checks.push(
          mark(cardNo, luhn(digits) ? "" : t("This card number is not valid.")),
          mark(cardName, cardName.value.trim() ? "" : t("Please enter the name on the card.")),
          mark(expiry, mm >= 1 && mm <= 12 && expEnd > now ? "" : t("Please enter a valid expiry date.")),
          mark(cvc, new RegExp(brand(digits) === "Amex" ? "^\\d{4}$" : "^\\d{3}$").test(cvc.value) ? "" : t("Please enter the security code.")));
      }
      const ok = checks.every(Boolean);
      if (!ok) view.querySelector("[aria-invalid=true]")?.focus();
      return ok;
    }

    async function submit(e) {
      e.preventDefault();
      formError.textContent = payError.textContent = "";
      if (!validate()) return;
      const digits = cardNo.value.replace(/\D/g, "");
      const payment = payMethod === "card" ? { method: "card", card_brand: brand(digits), card_last4: digits.slice(-4) }
                                           : { method: "cod" };
      placeBtn.disabled = true;
      placeBtn.textContent = t("Placing your order…");
      try {
        const order = await api("/api/orders", { method: "POST", body: JSON.stringify({
          items: lines().map(({ item, qty }) => ({ id: item.id, qty })), fulfilment,
          contact: { name: name.value.trim(), phone: phone.value.trim(), notes: notes.value.trim() || null,
                     address: fulfilment === "delivery" ? address.value.trim() : null },
          payment }) });
        cart = {};
        write(localStorage, CART_KEY, cart);
        write(sessionStorage, LAST_ORDER_KEY, { id: order.id, name: order.contact.name.split(" ")[0] });
        renderCart();
        location.hash = `#/order/${order.id}`;
      } catch (err) {
        const target = err.status === 402 ? payError : formError;
        target.textContent = t(err.message);  // server messages are in i18n.json too
        target.scrollIntoView({ behavior: "smooth", block: "center" });
        placeBtn.disabled = false;
        renderSummary();
      }
    }

    view.replaceChildren(h("section", { class: "wrap page" },
      h("a", { class: "back", href: "#/" }, t("← Back to menu")),
      h("h1", {}, t("Checkout")),
      h("form", { class: "checkout", novalidate: true, onsubmit: submit },
        h("div", { class: "checkout-main" },
          h("fieldset", {}, h("legend", {}, t("1. How would you like it?")),
            h("div", { class: "radio-row" },
              radioCard("mode", "delivery", t("Delivery"), t("About 30 min · {fee}, free over {amount}", { fee: fmt(menu.delivery_fee), amount: fmt(menu.free_delivery_from) }), fulfilment === "delivery", () => setMode("delivery")),
              radioCard("mode", "pickup", t("Pickup"), t("Ready in about 15 min · free"), fulfilment === "pickup", () => setMode("pickup")))),
          h("fieldset", {}, h("legend", {}, t("2. Your details")),
            h("div", { class: "two" }, field(t("Full name"), name), field(t("Phone"), phone)),
            addressField,
            field(t("Notes for the kitchen or rider (optional)"), notes)),
          h("fieldset", {}, h("legend", {}, t("3. Payment")),
            h("div", { class: "radio-row" },
              radioCard("pay", "card", t("Card"), "Visa, Mastercard, Amex", true, () => setPay("card")), codCard),
            cardPanel, payError)),
        h("aside", { class: "checkout-summary" }, h("h2", {}, t("Your order")), summary, formError, placeBtn,
          h("p", { class: "muted small" }, t("By placing your order you agree to be contacted about this delivery."))))));
    setMode(fulfilment);
    refreshCheckout = renderSummary;
  }

  async function renderOrder(id) {
    view.replaceChildren(h("section", { class: "wrap page narrow" }, h("p", { class: "muted" }, t("Loading your order…"))));
    let order;
    try {
      order = await api(`/api/orders/${encodeURIComponent(id)}`);
    } catch (err) {
      view.replaceChildren(h("section", { class: "wrap page narrow" }, h("h1", {}, t("Order not found")),
        h("p", {}, t("We couldn't find an order with the number {id}. Check the number on your confirmation.", { id })),
        h("a", { class: "btn btn-primary", href: "#/track" }, t("Try another number"))));
      return;
    }
    const last = read(sessionStorage, LAST_ORDER_KEY);
    const fresh = last && last.id === order.id;
    const done = order.step === order.steps.length - 1;
    const pickup = order.fulfilment === "pickup", min = Math.max(1, order.eta_minutes);
    const etaText = done ? (pickup ? t("Ready for pickup") : t("Delivered. Enjoy your meal!"))
      : pickup ? t("Ready in about {min} min", { min }) : t("Arriving in about {min} min", { min });
    const pay = order.payment.method === "card" ? t("Paid by card") : pickup ? t("Pay at pickup") : t("Cash on delivery");
    const placed = new Date(order.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    view.replaceChildren(h("section", { class: "wrap page narrow" },
      h("div", { class: "order-head" },
        h("div", { class: "check", "aria-hidden": "true" }, "✓"),
        h("div", {}, h("h1", {}, fresh ? t("Thanks, {name}! Your order is in.", { name: last.name }) : t("Order {id}", { id: order.id })),
          h("p", { class: "muted" }, fresh ? t("Order number {id}. Keep it to track your order or ask our assistant.", { id: order.id })
            : (pickup ? t("Pickup · placed {time}", { time: placed }) : t("Delivery · placed {time}", { time: placed }))))),
      h("div", { class: "eta" }, etaText),
      h("ol", { class: "timeline" }, order.steps.map((s, i) =>
        h("li", { class: i < order.step ? "done" : i === order.step ? "current" : "" }, t(STEP_LABELS[s])))),
      h("div", { class: "order-box" },
        h("h2", {}, t("Order details")),
        order.items.map((it) => h("div", { class: "sum-row" }, h("span", {}, `${it.qty} × ${it.name}`),
          h("span", {}, it.price == null ? t("Priced at the kitchen") : fmt(it.price * it.qty)))),
        h("hr"),
        order.totals.subtotal ? [
          h("div", { class: "sum-row" }, h("span", {}, pickup ? t("Pickup") : t("Delivery")),
            h("span", {}, order.totals.delivery_fee ? fmt(order.totals.delivery_fee) : t("Free"))),
          h("div", { class: "sum-row total" }, h("span", {}, t("Total")), h("span", {}, fmt(order.totals.total)))] : null,
        h("p", { class: "muted" }, pay)),
      h("div", { class: "hero-actions" },
        h("a", { class: "btn btn-ghost", href: "#/" }, t("Order something else")),
        h("button", { class: "btn btn-ghost", type: "button", "data-open-chat": t("Where is my order {id}?", { id: order.id }) }, t("Get help with this order")))));
    if (!done) pollTimer = setInterval(() => { if (location.hash === `#/order/${id}`) renderOrder(id); }, 30000);
  }

  function renderTrack() {
    const input = h("input", { id: "t-id", placeholder: "FF-2001", autocomplete: "off", maxlength: "12", required: true });
    view.replaceChildren(h("section", { class: "wrap page narrow" },
      h("h1", {}, t("Track your order")),
      h("p", { class: "muted" }, t("Enter the order number from your confirmation.")),
      h("form", { class: "track-form", onsubmit: (e) => {
        e.preventDefault();
        if (input.value.trim()) location.hash = `#/order/${encodeURIComponent(input.value.trim().toUpperCase())}`;
      } }, h("label", { class: "sr-only", for: "t-id" }, t("Order number")), input,
        h("button", { class: "btn btn-primary", type: "submit" }, t("Track"))),
      h("p", { class: "muted small" }, t("You can also ask our assistant: it answers in ten languages."))));
    input.focus();
  }

  // ---------- router ----------
  function route(scrollTop = true) {
    clearInterval(pollTimer);
    const [, page, arg] = (location.hash || "#/").split("/");
    if (!menu) return;
    refreshCheckout = null;
    if (page === "checkout") renderCheckout();
    else if (page === "order" && arg) renderOrder(decodeURIComponent(arg));
    else if (page === "track") renderTrack();
    else renderHome();
    renderCart();
    if (scrollTop) window.scrollTo(0, 0);
  }

  async function init() {
    $("cart-btn").addEventListener("click", openCart);
    $("cart-close").addEventListener("click", closeCart);
    $("scrim").addEventListener("click", closeCart);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("cart").hidden) closeCart(); });
    window.addEventListener("hashchange", () => route());
    window.addEventListener("feastfleet:cart-add", (e) => {  // a dish the assistant matched (chat.js)
      const { id, qty } = e.detail || {};
      if (!menu?.byId[id]) return;
      setQty(id, (cart[id] || 0) + (qty || 1));
      toast(t("{name} added to cart", { name: menu.byId[id].name }));
    });
    $("search").addEventListener("input", (e) => {
      query = e.target.value;
      category = "All";
      if ((location.hash || "#/") !== "#/") location.hash = "#/"; else route(false);
    });
    window.addEventListener("feastfleet:lang", () => route(false));  // the store language changed (i18n.js)
    renderCart();
    await window.FF_I18N.ready;
    try {
      menu = await api("/api/menu");
      menu.byId = Object.fromEntries(menu.items.map((m) => [m.id, m]));
      for (const id of Object.keys(cart)) if (!menu.byId[id]) delete cart[id];  // dishes removed from the menu
    } catch {
      view.replaceChildren(h("section", { class: "wrap page narrow" }, h("h1", {}, t("We'll be right back")),
        h("p", {}, t("The menu could not be loaded. Please try again in a moment.")),
        h("button", { class: "btn btn-primary", type: "button", onclick: () => location.reload() }, t("Try again"))));
      return;
    }
    renderCart();
    route();
  }
  init();
})();
