# Overlay & Popup Blocking — Options Specification

## Problem

When capturing screenshots or extracting text via Browserless, intrusive overlays
block the underlying page content. These include:

- Cookie / GDPR consent banners
- Newsletter subscription popups
- Login / registration walls
- Survey and feedback modals
- "Download our app" prompts
- Age-verification gates
- Notification permission dialogs
- Ad overlays and interstitials

> **Why not `blockConsentModals`?**
> `blockConsentModals` is a Browserless **Cloud/Enterprise-only** feature. Self-hosted
> community instances (including the Home Assistant add-on) return `400 Bad Request`
> when the parameter is included anywhere in the request — whether in the JSON body
> or as a URL query string. It is therefore omitted from all requests.

---

## Shared DOM Fingerprint

All blocking overlays share the same structural signals regardless of their purpose:

| Signal | Why it's reliable |
|---|---|
| `position: fixed` or `sticky` | Must be viewport-anchored to block content |
| `z-index > 100` | Must sit above all page content |
| Large viewport coverage | Designed to block what is behind them |
| `body { overflow: hidden }` | Page scroll is locked while modal is open |
| `[role="dialog"]` / `[aria-modal]` | Semantic accessibility markers |

Targeting these structural signals catches **all** overlay types without needing to
maintain lists of class names or vendor-specific selectors.

---

## Options

### Option 1 — Z-index + Position Heuristic ✅ Implemented

**How it works:** After page load, sweep all elements and remove any that are
`position: fixed` or `position: sticky` with a `z-index` above a threshold (99).
Also restores `overflow` on `<body>` and `<html>` which overlays commonly lock.

Safe tags (`HEADER`, `NAV`, `FOOTER`, `SCRIPT`, `STYLE`, `LINK`) are excluded
to avoid removing legitimate page chrome.

**Delivery:** Injected as an `addScriptTag` entry in the Browserless `/content`
payload — no external dependencies, no network requests.

```javascript
(function () {
    // Restore any scroll lock the overlay may have imposed
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';

    const SAFE_TAGS = new Set(['HEADER', 'NAV', 'FOOTER', 'SCRIPT', 'STYLE', 'LINK']);
    const Z_INDEX_THRESHOLD = 99;

    document.querySelectorAll('*').forEach(function (el) {
        if (SAFE_TAGS.has(el.tagName)) return;
        var s = window.getComputedStyle(el);
        var z = parseInt(s.zIndex, 10);
        if (
            (s.position === 'fixed' || s.position === 'sticky') &&
            !isNaN(z) &&
            z > Z_INDEX_THRESHOLD
        ) {
            el.remove();
        }
    });
})();
```

**Pros:**
- Works on any overlay type — no selector list to maintain
- Self-contained, no external dependencies
- Handles cookie banners, newsletter popups, login walls, survey modals etc.

**Cons:**
- May clip sticky toolbars that legitimately use high z-index (rare in practice)
- Runs once after `networkidle2`; won't catch overlays injected after that point

**Controlled by:** "Block Overlays" switch entity in device controls.

---

### Option 2 — Body Overflow Unlock + Backdrop Removal

**How it works:** Detects the "modal is active" signal — `body { overflow: hidden }` —
and removes any element whose class or id contains `backdrop`, `overlay`, or `mask`.

```javascript
if (
    document.body.style.overflow === 'hidden' ||
    window.getComputedStyle(document.body).overflow === 'hidden'
) {
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
    document.querySelectorAll(
        '[class*="backdrop"],[class*="overlay"],[class*="mask"]'
    ).forEach(function (el) { el.remove(); });
}
```

**Pros:** Very low false-positive risk — only triggers when scroll is explicitly locked.
**Cons:** Only activates if the site uses the scroll-lock pattern; misses overlays
that do not lock scroll.

**Status:** Not yet implemented. Could be combined with Option 1 as a second pass.

---

### Option 3 — Semantic Role Targeting

**How it works:** Targets elements with ARIA dialog roles, which are the correct
semantic markup for modal dialogs regardless of visual styling.

```javascript
document.querySelectorAll(
    '[role="dialog"],[role="alertdialog"],[aria-modal="true"]'
).forEach(function (el) { el.remove(); });
```

**Pros:** Zero false positives — only removes elements explicitly marked as dialogs.
**Cons:** Not all popups use ARIA roles correctly; many cookie banners and newsletter
modals omit semantic markup entirely.

**Status:** Not yet implemented. Good candidate to combine with Option 1.

---

### Option 4 — MutationObserver (SPA / Delayed Popups)

**How it works:** Injects a `MutationObserver` that watches for elements being added
to the DOM after initial load and immediately removes any that match the z-index
heuristic. Catches popups that fire after a delay (e.g. "subscribe after 5 seconds")
or are injected by React/Vue/Angular hydration.

```javascript
new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
        m.addedNodes.forEach(function (node) {
            if (node.nodeType !== 1) return;
            var s = window.getComputedStyle(node);
            var z = parseInt(s.zIndex, 10);
            if (
                (s.position === 'fixed' || s.position === 'sticky') &&
                !isNaN(z) && z > 99
            ) {
                node.remove();
            }
        });
    });
}).observe(document.body, { childList: true, subtree: true });
```

**Pros:** Catches delayed popups and SPA-injected modals that appear after load.
**Cons:** Observer must be injected early enough to catch all mutations; adds overhead
for the duration of the page session.

**Status:** Not yet implemented. Most valuable addition after Option 1 for React/Next.js sites.

---

### Option 5 — Browserless `/function` Endpoint

**How it works:** Replace the `/content` REST call with Browserless's `/function`
endpoint which provides a full Puppeteer context. Navigate to the page, wait a
configurable delay for delayed popups to appear, run cleanup, then return `page.content()`.

**Pros:**
- Most powerful — full programmatic control over timing and interaction
- Can click "Accept"/"Close" buttons rather than force-removing elements
- Handles auth walls, age gates, and other interactive flows

**Cons:**
- Requires a different code path / endpoint
- More complex payload; harder to maintain
- `/function` payloads are not validated the same way as `/content`

**Status:** Not yet implemented. Best option if Options 1–4 prove insufficient.

---

## Implementation Notes

- All script injection uses the Browserless `addScriptTag` payload field, which
  is supported by self-hosted community instances.
- Options 1, 2, and 3 are combinable in a single `addScriptTag` entry.
- Option 4 (MutationObserver) should be injected as a separate early script tag
  before the page navigates, which requires either a `waitFor` approach or the
  `/function` endpoint.
- The feature is gated behind the **"Block Overlays"** switch entity so users can
  disable it per-scraper if it causes issues on a specific site.
