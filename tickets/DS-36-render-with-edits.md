# DS-36 — Renders apply the edits

**Track:** Video editing · **Size:** M · **Depends on:** [DS-03](DS-03-render-params-record.md), [DS-34](DS-34-framing-filters.md), [DS-35](DS-35-trimmed-offset.md) · **Spec:** [video-editing.md](../specs/video-editing.md)

## Context

The spec names the cache as the bug this feature is most likely to ship with: a render's filename must name everything it depends on, and so must the browser's URL.

## Scope

- Each video's edit chain runs before the fit `scale` in compare renders.
- Take-only renders keep the cropped resolution with no upscaling, rounded down to even dimensions.
- Trim on the take: `trim=start=S:end=E,setpts=PTS-STARTPTS` in clip time, before re-timing; `atrim` on room audio; the reference cut moved by `trimmed_offset`.
- A short hash of `(reference.framing, clip.framing, clip.trim)` goes into the render params record from DS-03, so it reaches both the cache name and the query string.

## Acceptance criteria

- Render dimensions after crop and rotate are correct, checked with ffprobe
- A changed edit produces a different cache id and a different browser URL
- Every edit looks the same in the preview and in the download
