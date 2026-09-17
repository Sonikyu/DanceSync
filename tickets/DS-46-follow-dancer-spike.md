# DS-46 — Spike: can we follow one dancer?

**Track:** Follow dancer · **Size:** L · **Depends on:** [DS-13](DS-13-job-queue.md) for anything built after it · **Spec:** [follow-dancer.md](../specs/follow-dancer.md)

## Context

Finding people in a frame is solved. Keeping track of the *same* person through a choreography is not: dancers cross, block each other, wear matching outfits, and move fast — exactly when off-the-shelf trackers swap identities. Like alignment, this gets proved on real material before any UI is built.

## Scope

- **Material:** at least 5 real group practice videos, 4–9 dancers, some fixed camera and some moving, some matching outfits. Hand-label one dancer's box every 2 s (~120 boxes per 4-minute video) with a small labeling script.
- **Pipeline:** detect people every Nth frame → multi-object tracker → the track the user would tap → a smoothed crop path.
- **Stack to evaluate:** a small YOLOX or RT-DETR exported to ONNX and run with `onnxruntime` (Ultralytics is the fastest way to try things but is AGPL-3.0, which matters if this is ever published); ByteTrack (MIT) for linking; appearance-based re-ID only if identity switches fail the gate.
- **Metrics:** share of labeled moments where the dancer's box center falls inside the crop; identity switches per minute; wall-clock tracking time for a 4-minute video.
- **Gate:** ≥95% kept in frame with no more than one manual correction per minute, on the fixed-camera videos.

## Outcome

A written go/no-go. If it passes, the product design in the spec gets broken into implementation tickets (tracking module, crop path, routes and job, picker UI, `sendcmd` render). If it fails, the fallback is [DS-47](DS-47-keyframed-crop.md), which needs no computer vision.

`onnxruntime` plus a model file of tens of MB would be the heaviest dependency in the project, so the spike has to show the result is worth it.

## Acceptance criteria

- The metrics are reported per video, not averaged into one number
- The go/no-go is explicit, with the gate numbers next to the measured ones
- No production code is added in this ticket; the spike lives beside the alignment spike
