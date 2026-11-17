# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, weighted equally (confirmed 2026-11-17):
- **People ordering dinner** in an Indian city: browsing a menu, ordering for delivery or pickup, paying by card or cash on delivery, then checking where the order is. Many are not comfortable in English; they may write in Hindi, Tamil, Arabic, Swahili, Amharic, Japanese, French, German, Spanish or English.
- **People evaluating the project** (markers, classmates) during a live demo: they need to believe the product and to see the multilingual AI assistant working, including its honest handoff to a person.

## Product Purpose

FeastFleet is a food-delivery storefront whose support assistant understands ten languages. It exists to demonstrate a multilingual intent-and-slot NLU model (XLM-R) inside a real-feeling ordering flow. Success: a visitor orders, pays and tracks without help, and any visitor can get help in their own language, or is handed to a person when the assistant is not sure.

## Positioning

Help in the customer's own language, with an assistant that says it is an AI and hands off instead of guessing. The ordering flow itself is conventional; the multilingual support is the difference.

## Operating Context

- Customers order from a phone or laptop, often in the evening; checkout must be quick and forgiving.
- The live demo runs on one laptop (`docker compose up`, `http://localhost:8080`); the presenter switches languages in the assistant to show detection, slot filling, order tracking and handoff.
- Orders placed on the site and in chat share one orders API, so an order from checkout can be tracked in chat.

## Capabilities and Constraints

- Menu with categories, cart, checkout (delivery or pickup; card or cash on delivery / pay at pickup), order confirmation with a status timeline, track-order page, assistant widget with a language picker.
- Prices in **Indian rupees**, Indian-first menu with other cuisines (confirmed 2026-11-17). The specific city is **not decided**: do not name one.
- Static site (HTML, CSS, vanilla JS), served by nginx with a strict Content-Security-Policy (`'self'` only): no external fonts, scripts or images. Anything visual must ship in the repository.
- Text must render in Latin, Devanagari, Tamil, Ethiopic (Amharic), Arabic (right-to-left) and Japanese scripts.
- Card payments are simulated: a visible test-mode marker stays on the card form, and card data never leaves the page (only brand and last four digits are sent).
- Orders live in memory (restarting the orders service clears them).

## Brand Commitments

- Name and logo are not fixed (confirmed 2026-11-17); FeastFleet is a **fictional** brand and one small footer line says so.
- **Look and feel: the Indian food-delivery app standard, sitting alongside Swiggy and Zomato** (user, 2026-11-17, after rejecting themed directions: "make it swiggy zomato"). Their conventions (white page, dish rows with an image tile and ADD button, veg/non-veg marker, bill details, sticky cart bar) at full craft; never their logos, names or exact brand colours.

## Evidence on Hand

- No real restaurants, reviews, ratings, delivery partners, customer counts or press. Do not invent any.
- Real: the assistant's measured behaviour (reports/evaluation_report.md, reports/dialogue_eval.md) and its ten-language replies (rasa/domain.yml, AI-written and not yet reviewed by native speakers).
- No food photography exists in the repository.

## Product Principles

1. Ordering comes first: the menu and checkout must work without the assistant.
2. Help in the customer's language is the promise; the assistant always says it is an AI and hands off when unsure.
3. Honest by default: no fabricated reviews, partners, ratings or claims; simulated payment is marked as such.
4. Every script is first-class: Arabic reads right-to-left, Indic and Ethiopic scripts are never squeezed or fall back badly.

## Accessibility & Inclusion

WCAG 2.2 AA contrast and keyboard access for ordering and the assistant; respect reduced-motion preferences; right-to-left support for Arabic.
