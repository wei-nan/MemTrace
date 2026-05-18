# MemTrace UI Style Guide

> **Zero-tolerance rule**: No colour changes. Only sizes, spacing, radius, and weight are governed here.

---

## Typography Scale

| Role | Size | Weight | Where used |
|---|---|---|---|
| Page h1 (settings) | 15px | 600 | SettingsPanel header |
| Section h3 / panel title | 14px | 600 | Card section headings, side panel titles |
| Body / labels / nav | 13px | 400–600 | Most UI text, table cells, input labels |
| Small / meta / timestamps | 12px | 400 | Subtitles, timestamps, helper text |
| Micro / badge labels | 11px | 600 | Orphan count chips, toolbar badges |
| Category labels (ALL CAPS) | 10px | 700 | Cluster labels, section dividers |

### Display / Stat values (exempt from above)
Large numeric stats in **Analytics cards only** may use 20–28px bold. These are intentional data-display elements, not app chrome.

### Chat messages
Chat bubble content uses 13px / line-height 1.5.

---

## Border Radius System

| Element type | Radius | Example |
|---|---|---|
| Mini tags, status dots, ACTIVE badge | 4–6px | `.tag`, `borderRadius: 4` |
| Buttons, inputs, select controls | 8px | `.btn`, `.mt-input-container` |
| Cards, panels, section containers, table wrapper | 10px | `.card`, `SectionCard` |
| Glass / overlay panels | 12px | `.glass-panel`, chat bubbles |
| Circular avatars / icon frames | 50% or diameter/2 | user avatar |

> **Never use 14, 16, 20, or 24** for standard UI surfaces.

---

## Button Sizes

Use the `Button` component variants only. Do **not** override height/padding unless matching one of these targets:

| Variant | Padding | Font | Approx height |
|---|---|---|---|
| `size="sm"` | 5px 10px | 12px | 26px |
| `size="md"` (default) | 7px 14px | 13px | 32px |
| `size="lg"` | 10px 20px | 14px | 38–40px |
| `variant="icon"` | 6px | — | 32px |

When overriding height directly, match **32px** (md) or **36px** (lg full-width CTA). Never use 42px or 48px in non-modal contexts.

### Button variants

| Variant | Use case |
|---|---|
| `primary` | Primary action per page (one per section) |
| `secondary` | Secondary / neutral actions |
| `ghost` | Icon-only or tertiary actions in toolbars |
| `danger` | Destructive actions (delete, revoke) |
| `link` | Inline text links only |

---

## Spacing

| Context | Value |
|---|---|
| Card padding `sm` | 10px |
| Card padding `md` | 16px |
| Card padding `lg` | 24px |
| Section vertical gap | 20–24px |
| Item row gap (lists) | 8–12px |
| Toolbar item gap | 6–8px |
| Inline icon–text gap | 6–8px |

---

## Toolbar & Filter Bar Height

All toolbar controls (buttons, selects, tab buttons) should be **height: 32px**. Match this consistently:

```tsx
// Filter/tab button — override if needed
style={{ height: 32, padding: "0 12px" }}

// Select control in toolbar
style={{ height: 32, fontSize: 13, padding: "0 10px" }}

// Icon-only square button
style={{ height: 32, width: 32, padding: 0 }}
```

---

## Component-specific Rules

### `Card` component
Always use `<Card variant="surface|elevated|glass|outline" padding="sm|md|lg">`.
Never apply `borderRadius` inline on a `<Card>` — it is already set in `Card.css` to 10px.

### `Button` component
Always use the `<Button>` component. Avoid raw `<button className="btn-primary">` unless in CSS-class-driven patterns from `index.css`.

### `Input` component
Use `<Input>` or `<input className="mt-input">`. Do not override `borderRadius` or `fontSize` on inputs.

### Section headings inside cards
```tsx
<h3 style={{ fontSize: 14, margin: "0 0 16px", fontWeight: 600 }}>Section Title</h3>
```

### Page-level h1 (settings pages)
```tsx
<h1 style={{ fontSize: 15, marginBottom: 8 }}>Page Title</h1>
```

---

## Exemptions

These elements are intentionally larger and should **not** be normalised:

| Element | Reason |
|---|---|
| Auth / Onboarding full-screen headings | Fullscreen hero context |
| Analytics stat values (`fontSize: 20–28`) | Data display, not app chrome |
| Graph node labels | Canvas-rendered, separate scale |
| Chat bubble `borderRadius: 12` | Conventional chat UI |
| Circular avatar `borderRadius: 50%` / `diameter/2` | Circular by design |

---

## Quick Checklist (PR review)

- [ ] No `fontSize` above **15px** for app chrome text
- [ ] No `borderRadius` of 12, 14, 16, or 20 on cards / panels (use 10)
- [ ] No `borderRadius` of 10, 12, or 16 on buttons / inputs (use 8)
- [ ] No `height: 42` or `height: 48` on toolbar controls (use 32 or 36)
- [ ] No inline colour overrides (use CSS variables only)
- [ ] `Button` component used instead of raw `<button className="btn-*">`
- [ ] Section `<h3>` at 14px/600, page `<h1>` at 15px/600
