// Pure helpers for tuning an alignment by hand on Watch, and for placing a
// take by hand when the matcher found nothing. No React, no network.

import { effectiveAlignment, formatRate, formatTime } from "./flow.js";

// The same bounds the server checks (MIN_MANUAL_RATE / MAX_MANUAL_RATE).
export const MANUAL_RATE_MIN = 0.25;
export const MANUAL_RATE_MAX = 1;
export const RATE_STEP = 0.005;

// Practice speeds to pick from when placing a take by hand.
export const PRACTICE_RATES = [1, 0.75, 0.5];

// `alignment` ({ rate, offset_sec }) moved by `offsetMs` milliseconds and
// `rateSteps` steps of RATE_STEP. Rounded to whole milliseconds and to
// thousandths of a rate, so repeated nudges never pile up float error, and
// the rate is kept inside the bounds the server accepts.
export function nudgeAlignment(alignment, offsetMs, rateSteps) {
  const offsetSec = Math.round(alignment.offset_sec * 1000 + offsetMs) / 1000;
  const rate = Math.round((alignment.rate + rateSteps * RATE_STEP) * 1000) / 1000;
  return {
    rate: Math.min(Math.max(rate, MANUAL_RATE_MIN), MANUAL_RATE_MAX),
    offset_sec: offsetSec,
  };
}

// The offset nudge for a key press while tuning: ← and → move 10 ms, or
// 100 ms with Shift. Null for any other key.
export function offsetNudgeForKey(key, shiftKey) {
  const direction = { ArrowLeft: -1, ArrowRight: 1 }[key];
  if (direction === undefined) return null;
  return direction * (shiftKey ? 100 : 10);
}

// "1:05.23" for 65.234 s: formatTime to hundredths, for tuning in 10 ms steps.
export function formatPreciseTime(sec) {
  const hundredths = Math.round(Math.abs(sec) * 100);
  const sign = sec < 0 && hundredths > 0 ? "-" : "";
  const minutes = Math.floor(hundredths / 6000);
  const seconds = ((hundredths % 6000) / 100).toFixed(2).padStart(5, "0");
  return `${sign}${minutes}:${seconds}`;
}

// "0.750×": three decimals, since tuning moves the rate in 0.005 steps.
export function formatTunedRate(rate) {
  return `${rate.toFixed(3)}×`;
}

// The line under the player: where the take sits in the song and at what
// speed, and whether the dancer set that by hand.
export function alignmentSummary(clip) {
  const alignment = effectiveAlignment(clip);
  if (clip.alignment.manual) {
    return `Adjusted by hand · ${formatPreciseTime(alignment.offset_sec)} · ${formatTunedRate(alignment.rate)} speed`;
  }
  return `Matched at ${formatTime(alignment.offset_sec)} · ${formatRate(alignment.rate)}`;
}
