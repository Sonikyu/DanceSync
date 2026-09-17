# DS-29 — Pick a layout on Watch

**Track:** Layouts · **Size:** S · **Depends on:** [DS-20](DS-20-segmented-control.md), [DS-28](DS-28-layout-api.md) · **Spec:** [layouts.md](../specs/layouts.md)

## Context

Today a CSS media query decides side-by-side or stacked and the user has no say, while the downloads offer a different pair of options than the screen shows. What you see should be what you download.

## Scope

- `LayoutToggle.jsx` using `Segmented`: Side by side, Stacked, Take only.
- A layout class on `.compare` (`.side-by-side` row, `.stacked` column) replaces the media query in `styles.css`.
- Default: side by side on wide screens, stacked on narrow — matching today. The pick lives in `App` state so it carries to the next take in the session.
- The two download buttons become one, rendering the current layout and sound.
- An audio-only reference has only Take only, so the picker is hidden.

## Acceptance criteria

- All three layouts preview and download, and each download matches its preview
- Stacked plays in a browser `<video>` (even dimensions, baseline profile)
- With an audio-only reference only the take is offered, as today
- `flow.test.js` covers the default layout per viewport width and reference type
