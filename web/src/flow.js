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
export function chosenIndex(clip) {
  return clip.alignment.selected_index ?? 0;
}

export function chosenCandidate(clip) {
  return clip.alignment.top_candidates[chosenIndex(clip)];
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
