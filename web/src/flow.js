// Pure helpers for the step flow and for display formatting. No React and no
// network, so every one of them is covered by plain unit tests.

// The header dots show three stages. Checking an ambiguous match counts as
// part of the video stage, so the dots never skip ahead when it's not needed.
// "No match" stands in for the player, so it's the watch stage.
export const STAGES = ["Song", "Video", "Watch"];

const STAGE_OF_STEP = { song: 0, video: 1, match: 1, watch: 2, nomatch: 2 };

export function stageOf(step) {
  return STAGE_OF_STEP[step];
}

// A failed match skips the candidate picker: none of the candidates is good.
export function stepAfterAlignment(clip) {
  if (clip.alignment.failed) return "nomatch";
  return clip.alignment.ambiguous ? "match" : "watch";
}

// "That video is 6 seconds long. A take needs at least 10 seconds…"
export function clipTooShortMessage(durationSec, minSec) {
  const seconds = Math.max(1, Math.round(durationSec));
  return (
    `That video is ${seconds} second${seconds === 1 ? "" : "s"} long. ` +
    `A take needs at least ${minSec} seconds of dancing to the song, so it can be matched.`
  );
}

// The user's pick if they made one, else the matcher's best guess -- the same
// rule the server applies when it renders.
function chosenIndex(clip) {
  return clip.alignment.selected_index ?? 0;
}

export function chosenCandidate(clip) {
  return clip.alignment.top_candidates[chosenIndex(clip)];
}

// What a /synced render depends on, for api.syncedVideoUrl: the clip's song,
// the alignment it plays at, and which render.
export function renderParams(clip, sound, layout) {
  const candidate = chosenCandidate(clip);
  return {
    reference_id: clip.reference_id,
    rate: candidate.rate,
    offset_sec: candidate.offset_sec,
    layout,
    sound,
  };
}

// The option `step` places (+1 or -1) after `value` in a segmented control,
// wrapping around and skipping disabled ones. Null when nothing else is
// enabled.
export function nextOption(options, value, step) {
  const count = options.length;
  const start = Math.max(options.findIndex((option) => option.value === value), 0);
  for (let moved = 1; moved < count; moved++) {
    const option = options[(((start + step * moved) % count) + count) % count];
    if (!option.disabled) return option.value;
  }
  return null;
}

// "strongest match" for the winner, "93% as strong" for each runner-up.
export function strengthLabel(candidates, index) {
  if (index === 0) return "strongest match";
  const percent = Math.round((candidates[index].score / candidates[0].score) * 100);
  return `${percent}% as strong`;
}

// Where the reference video should be when the synced take is at `takeSec`
// (the take starts at `offsetSec` in the song). Null while the song hasn't
// started yet -- a negative offset means the phone started recording first.
export function referenceTimeFor(takeSec, offsetSec) {
  const referenceSec = offsetSec + takeSec;
  return referenceSec < 0 ? null : referenceSec;
}

// Playing the raw take in the browser uses the timing dancesync/sync.py
// renders with (see its module docstring, invariant 6). Output time T is what
// the play bar shows, 0 to the take's length × rate. At T the raw take is at
// clip time T / rate, playing at 1 / rate (a 0.75× take plays at 1.333×),
// and the song is at offsetSec + T (referenceTimeFor), playing at 1. These
// two are the browser's only conversions between clip and output time.
export function clipTimeFor(outputSec, rate) {
  return outputSec / rate;
}

export function outputTimeFor(clipSec, rate) {
  return clipSec * rate;
}

// Wide enough to show the reference and the take side by side by default.
export const WIDE_VIEWPORT_QUERY = "(min-width: 720px)";

// The layout to show and download ("side-by-side", "stacked" or "take"):
// the dancer's pick if they made one, else side by side on a wide screen and
// stacked on a narrow one. A song file with no picture only has the take.
export function layoutFor({ picked, wideViewport, hasReferenceVideo }) {
  if (!hasReferenceVideo) return "take";
  if (picked) return picked;
  return wideViewport ? "side-by-side" : "stacked";
}

// Review speeds, as fractions of the song's tempo.
export const REVIEW_SPEEDS = [0.5, 0.75, 1];

// `playbackRate`s for reviewing at `speed`. The song always plays at `speed`.
// `rate` is the take media's own speed relative to the song: 1 for a
// rendered take, which is already at full tempo, or the matched rate for the
// raw clip, which then plays at speed / rate -- exactly 1.0, as filmed, when
// the dancer reviews at the speed they practised.
export function playbackRates({ rate, speed }) {
  return { take: speed / rate, reference: speed };
}

// The element making the sound is the clock and the muted one follows it:
// nudging a muted video's speed is invisible, nudging audio warbles. The
// song plays from the reference element, the room from the take.
export function leaderFor(sound) {
  return sound === "room" ? "take" : "reference";
}

// Where an offset sits along the song, as a CSS percentage clamped to the bar.
export function timelinePercent(offsetSec, durationSec) {
  return Math.min(Math.max(offsetSec / durationSec, 0), 1) * 100;
}

// "1:05" for 65.2 s. Offsets can be negative when the phone started
// recording before the song did.
export function formatTime(sec) {
  const whole = Math.round(Math.abs(sec));
  const sign = sec < 0 && whole > 0 ? "-" : "";
  const seconds = String(whole % 60).padStart(2, "0");
  return `${sign}${Math.floor(whole / 60)}:${seconds}`;
}

export function formatRate(rate) {
  return rate === 1 ? "full speed" : `${rate}× speed`;
}

export function songTitle(filename) {
  return filename.replace(/\.[^.]+$/, "");
}
