# DS-39 — Trim the take

**Track:** Video editing · **Size:** S · **Depends on:** [DS-35](DS-35-trimmed-offset.md), [DS-38](DS-38-adjust-ui.md) · **Spec:** [video-editing.md](../specs/video-editing.md)

## Context

Takes usually start and end with the dancer walking to and from the phone.

## Scope

- Two buttons, **Set start here** and **Set end here**, using the current play position. Easier on a phone than two handles on a scrubber.
- The preview honours the trim: playback starts at the new start and stops at the new end.
- Saved with the clip edits PUT from DS-33.

## Out of scope

Cutting out the middle of a take.

## Acceptance criteria

- A trimmed take previews and downloads with the same first and last frame
- Alignment is not re-run when a trim changes
