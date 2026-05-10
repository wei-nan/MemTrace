# MemTrace Design System

> Version: 3.0  
> Last synced: 2026-05-10  
> Source of truth: `packages/ui/src/index.css` and `packages/ui/src/components/ui/*`  
> Scope: React UI, shared CSS tokens, shared UI primitives, SVG assets, and application-level visual conventions.

This document describes the current MemTrace UI style. It replaces the older green-only design guidance. The implemented UI now uses a teal primary color, restrained secondary accents, glass-style surfaces, and shared UI primitives.

## Principles

1. Use tokens first.
   Colors, borders, shadows, backgrounds, and text colors must come from CSS variables in `index.css`.

2. Prefer shared UI primitives.
   New UI should use `Button`, `Input`, `Card`, and `Modal` from `packages/ui/src/components/ui` before adding raw elements.

3. Keep product UI quiet and work-focused.
   MemTrace is a knowledge/workspace tool. Avoid marketing-style hero layouts, decorative gradients, oversized typography in panels, and excessive visual ornament.

4. Use accents sparingly.
   Teal is the primary product color. Indigo, pink, and provider colors are available but must not become competing brand colors.

5. Avoid hard-coded visual values.
   Hard-coded hex colors, one-off border radii, and custom shadows should be treated as legacy unless required for graph semantics or third-party visualization APIs.

6. Maintain light/dark parity.
   Any visual change must work in both `:root[data-theme="dark"]` and `:root[data-theme="light"]`.

## Current Token Model

Tokens live in [index.css](/Users/shiweinan/Workspace/MemTrace/packages/ui/src/index.css).

### Dark Theme

```css
:root,
:root[data-theme="dark"] {
  --bg-base:        #0B0D11;
  --bg-surface:     #15181E;
  --bg-elevated:    #1E222A;
  --bg-overlay:     rgba(0, 0, 0, 0.75);

  --glass-bg:       rgba(21, 24, 30, 0.75);
  --glass-border:   rgba(255, 255, 255, 0.08);
  --glass-shadow:   0 8px 32px 0 rgba(0, 0, 0, 0.37);
  --glass-blur:     12px;

  --color-primary:        #2DD4BF;
  --color-primary-hover:  #14B8A6;
  --color-primary-subtle: rgba(45, 212, 191, 0.12);
  --color-primary-glow:   rgba(45, 212, 191, 0.35);

  --color-secondary:      #818CF8;
  --color-accent:         #F472B6;

  --border-subtle:  rgba(255, 255, 255, 0.04);
  --border-default: rgba(255, 255, 255, 0.08);
  --border-strong:  rgba(255, 255, 255, 0.14);

  --text-primary:    #F8FAFC;
  --text-secondary:  #94A3B8;
  --text-muted:      #64748B;
  --text-disabled:   #334155;
  --text-on-primary: #0F172A;

  --input-bg:          rgba(15, 23, 42, 0.32);
  --input-bg-hover:    rgba(15, 23, 42, 0.42);
  --input-bg-focus:    rgba(15, 23, 42, 0.52);
  --input-disabled-bg: rgba(15, 23, 42, 0.18);
  --input-border:      var(--border-default);
  --input-border-hover: var(--border-strong);
}
```

### Light Theme

```css
:root[data-theme="light"] {
  --bg-base:        #F8FAFC;
  --bg-surface:     #FFFFFF;
  --bg-elevated:    #F1F5F9;
  --bg-overlay:     rgba(15, 23, 42, 0.45);

  --glass-bg:       rgba(255, 255, 255, 0.85);
  --glass-border:   rgba(15, 23, 42, 0.08);
  --glass-shadow:   0 8px 32px 0 rgba(31, 38, 135, 0.07);
  --glass-blur:     8px;

  --color-primary:        #0D9488;
  --color-primary-hover:  #0F766E;
  --color-primary-subtle: rgba(13, 148, 136, 0.08);
  --color-primary-glow:   rgba(13, 148, 136, 0.2);

  --border-subtle:  #F1F5F9;
  --border-default: #E2E8F0;
  --border-strong:  #CBD5E1;

  --text-primary:    #0F172A;
  --text-secondary:  #475569;
  --text-muted:      #64748B;
  --text-disabled:   #94A3B8;
  --text-on-primary: #FFFFFF;

  --input-bg:          #FFFFFF;
  --input-bg-hover:    #FFFFFF;
  --input-bg-focus:    #FFFFFF;
  --input-disabled-bg: #F1F5F9;
  --input-border:      #CBD5E1;
  --input-border-hover: #94A3B8;
}
```

## Color Usage

### Primary

Use `--color-primary` for:

- Primary buttons
- Active navigation states
- Focus rings
- Key icons
- Important action affordances

Do not override `--color-primary` inside a component.

### Secondary And Accent

Use `--color-secondary` and `--color-accent` only when a feature needs a secondary visual category. They are not replacement brand colors.

Valid uses:

- Distinguishing AI/provider-related metadata
- Graph/category accents
- Rare supporting highlights

Invalid uses:

- Making entire pages indigo or pink
- Replacing primary button color
- Creating decorative background blobs or gradients

### Status Colors

Use status colors only for state:

| Token | Use |
|---|---|
| `--color-success` | Completed, valid, healthy |
| `--color-warning` | Pending, risky, needs attention |
| `--color-error` | Failed, destructive, invalid |
| `--color-info` | Informational status |

Status colors should have subtle background variants when used as badges or alert surfaces.

### AI Provider Colors

Provider colors exist for provider labels, model menus, and usage indicators:

| Provider | Token |
|---|---|
| OpenAI | `--ai-openai` |
| Anthropic | `--ai-anthropic` |
| Gemini | `--ai-gemini` |
| Ollama | `--ai-ollama` |

Provider colors must not be used as general UI colors.

## Typography

Fonts are loaded in `index.css`.

| Use | Font | Weight |
|---|---|---|
| Body text | `Inter` | 400-600 |
| Headings | `Outfit` | 600-700 |
| Code / technical inline data | `JetBrains Mono` | 400-500 |

Rules:

- Do not scale type with viewport width.
- Do not use negative letter spacing in compact panels.
- Use 13-14px for dense operational UI labels and body rows.
- Use 15-18px for panel headings.
- Reserve large display type for true first-screen product surfaces, not tool panels.

## Shared UI Primitives

Shared primitives live in [components/ui](/Users/shiweinan/Workspace/MemTrace/packages/ui/src/components/ui/index.ts).

New UI should import from:

```ts
import { Button, Input, Card, Modal } from './components/ui';
```

or from the correct relative path for nested components.

### Button

Implementation:

- [Button.tsx](/Users/shiweinan/Workspace/MemTrace/packages/ui/src/components/ui/Button.tsx)
- [Button.css](/Users/shiweinan/Workspace/MemTrace/packages/ui/src/components/ui/Button.css)

Variants:

| Variant | Use |
|---|---|
| `primary` | Main affirmative action |
| `secondary` | Common non-primary action |
| `danger` | Destructive action |
| `ghost` | Low-emphasis action |
| `link` | Inline text action |
| `icon` | Icon-only tool action |

Sizes:

| Size | Use |
|---|---|
| `sm` | Dense tables, compact toolbars |
| `md` | Default |
| `lg` | Dialog primary action or sparse settings panel |

Example:

```tsx
<Button variant="primary" loading={saving} onClick={handleSave}>
  Save
</Button>

<Button variant="icon" aria-label="Close" onClick={onClose}>
  <X size={16} />
</Button>
```

Rules:

- Use `loading`, not `isLoading`.
- Icon-only buttons must have `aria-label`.
- Prefer `variant="danger"` for destructive actions instead of inline red styles.
- Do not create new `.btn-*` classes unless adding a shared variant.

### Input

Implementation:

- [Input.tsx](/Users/shiweinan/Workspace/MemTrace/packages/ui/src/components/ui/Input.tsx)
- [Input.css](/Users/shiweinan/Workspace/MemTrace/packages/ui/src/components/ui/Input.css)

Example:

```tsx
<Input
  label="Workspace name"
  value={name}
  onChange={event => setName(event.target.value)}
  error={nameError}
/>
```

Rules:

- Use `Input` for new single-line text fields.
- Use `.mt-input` only for legacy code, selects, or textareas until shared `Select` / `Textarea` primitives exist.
- Error text should use the `error` prop where possible.
- Editable fields must use `--input-bg` and `--input-border`; disabled or readonly fields must use `--input-disabled-bg`.
- In light theme, editable fields should read as active white controls, not grey readonly surfaces.

### Card

Implementation:

- [Card.tsx](/Users/shiweinan/Workspace/MemTrace/packages/ui/src/components/ui/Card.tsx)
- [Card.css](/Users/shiweinan/Workspace/MemTrace/packages/ui/src/components/ui/Card.css)

Variants:

| Variant | Use |
|---|---|
| `surface` | Default panel/card |
| `elevated` | Active or emphasized surface |
| `glass` | Overlay-like translucent surface |
| `outline` | Selectable option or low-emphasis grouping |

Padding:

| Padding | Value |
|---|---|
| `none` | 0 |
| `sm` | 12px |
| `md` | 20px |
| `lg` | 32px |

Rules:

- Do not nest decorative cards inside decorative cards.
- Use cards for repeated items, modals, and framed tools.
- Page sections should generally be unframed layouts or full-width bands, not floating card stacks.

### Modal

Implementation:

- [Modal.tsx](/Users/shiweinan/Workspace/MemTrace/packages/ui/src/components/ui/Modal.tsx)
- [Modal.css](/Users/shiweinan/Workspace/MemTrace/packages/ui/src/components/ui/Modal.css)

Use `Modal` for custom dialogs and `AlertModal` / `ConfirmModal` through `ModalContext` for standard alerts and confirmations.

Rules:

- Dialog titles should be concise.
- Primary action goes right; secondary/cancel action goes left of primary.
- Destructive confirmation must use `variant="danger"`.
- Modal widths should be explicit and stable.

## Legacy Classes

The following global classes still exist and are allowed in existing screens:

| Class | Current status | Guidance |
|---|---|---|
| `.btn-primary` / `.btn-secondary` / `.btn-danger` / `.btn-ghost` / `.btn-link` / `.btn-icon` | Legacy-compatible | New code should prefer `Button` |
| `.mt-input` | Legacy-compatible | New text input should prefer `Input`; selects/textareas may still use `.mt-input` |
| `.glass-panel` | Legacy-compatible | Use for graph/node panels or existing glass surfaces |
| `.tag` | Legacy-compatible | Acceptable for simple tags until a shared `Badge` component exists |
| `.search-bar` / `.search-input` | Legacy-compatible | Acceptable for existing search UI |
| `.tabs` / `.tab` | Legacy-compatible | Acceptable until shared Tabs component exists |

When touching a legacy component, migrate opportunistically if the change is local and low risk.

## Menus, Selects, Toggles, And Tables

Shared primitives for Select, Toggle, Tabs, Badge, and Table do not yet exist. Until they do:

- Use `.mt-input` for `select` and textarea surfaces.
- Use `--bg-surface`, `--bg-elevated`, and border tokens for custom menus.
- Use `--color-primary-subtle` for selected states.
- Use status tokens for state badges.
- Avoid hard-coded menu shadows and colors.

Recommended future components:

- `Select`
- `Textarea`
- `Toggle`
- `Badge`
- `Tabs`
- `Table`
- `Tooltip`

## Layout Rules

- App shell uses `.app-container`, `.sidebar`, `.view-port`, and `.side-panel`.
- Sidebar width is 280px expanded and 72px collapsed.
- Dense tool surfaces should prefer 8px or 12px gaps.
- Large panels should use 16px to 24px padding.
- Fixed-format elements like graph controls, icon buttons, and toolbar controls should have stable dimensions.
- Text must not overflow buttons, cards, table cells, or panels. Use wrapping, truncation, or smaller local labels as needed.

## Graph UI

Graph colors are semantic and should use graph/node tokens:

| Token | Use |
|---|---|
| `--node-core` | High-trust or focused node |
| `--node-secondary` | Medium-trust node |
| `--node-leaf` | Lower-trust leaf node |
| `--node-faded` | Archived or faded node |
| `--edge-default` | Normal edge |
| `--edge-strong` | Strong or hover edge |

Graph libraries may require concrete color strings. Prefer deriving those strings from theme-aware palette helpers near the graph component rather than scattering literals across the app.

## Accessibility

- Icon-only buttons require accessible labels.
- Focus states must be visible and use `--color-primary-subtle`.
- Text and controls must meet contrast in both light and dark themes.
- Do not communicate state by color alone; pair color with text, icon, or shape.
- Modals must be dismissible by Escape and close affordance.

## Hard-Coded Values Policy

Avoid:

```tsx
style={{ color: '#ef4444' }}
style={{ background: '#10b981' }}
```

Prefer:

```tsx
style={{ color: 'var(--color-error)' }}
style={{ background: 'var(--color-success)' }}
```

Hard-coded colors are allowed only when:

- A third-party visualization API cannot use CSS variables directly.
- The value represents external brand identity, such as provider colors, and no token exists yet.
- The value is temporary and marked for migration.

## Prohibited Patterns

| Prohibited | Use instead |
|---|---|
| New raw `<button>` with hand-written button styles | `Button` |
| New raw `<input>` with hand-written input styles | `Input` |
| New modal made from fixed-position divs | `Modal` / `ModalContext` |
| Hard-coded hex colors | CSS tokens |
| Decorative gradients or background blobs | Token-based surfaces |
| Replacing primary color per feature | Provider/status tokens only where semantically relevant |
| Cards inside cards for page layout | Unframed layout, sections, or repeated item cards |

## Migration Checklist

When editing UI code:

- [ ] New buttons use `Button`.
- [ ] New text inputs use `Input`.
- [ ] New dialogs use `Modal` or `ModalContext`.
- [ ] New colors use CSS variables.
- [ ] Icon-only controls have labels.
- [ ] Light and dark themes are checked.
- [ ] Inline styles are limited to layout or dynamic values.
- [ ] Legacy `.btn-*` / `.mt-input` usage is not expanded unnecessarily.

## Known Gaps

The UI is not fully migrated yet. Existing screens still contain:

- Raw buttons with `className="btn-*"`
- Raw `input`, `select`, and `textarea` elements
- Inline layout styles
- Some hard-coded colors in older components
- Legacy `.glass-panel` surfaces

These are acceptable as transitional debt. New work should not add more unless there is a concrete reason.

## Logo Usage

Logo assets live under `packages/ui/public`.

| Asset | Use |
|---|---|
| `logo.svg` | Default |
| `logo-light.svg` | Light-background contexts |
| `logo-dark.svg` | Dark-background contexts |
| `favicon.svg` | Browser icon |

Rules:

- Do not recolor logo assets ad hoc in components.
- Sidebar/app shell should use the existing logo asset or token-colored icon treatment consistently.
- Icon-only logo usage must remain legible at 16px.

## Change History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-04-11 | Initial Indigo-based design guidance |
| 2.0 | 2026-04-27 | Green primary color, graph/provider tokens |
| 3.0 | 2026-05-10 | Synced to current teal/glass implementation; added shared UI primitive governance and legacy migration rules |
