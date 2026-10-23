// Pure helpers for editing how each video is shown on Watch (crop, mirror,
// rotate) and trimming the take. No React, no network.
//
// A framing is { rotate, crop, mirror }, applied in that order, the same
// order dancesync/framing.py renders it in. `crop` is { x, y, w, h }:
// fractions of the rotated, un-mirrored frame, origin top-left, or null for
// the whole frame. A trim is { start_sec, end_sec } in the take as filmed.

// The same floor the server checks (MIN_CROP_FRAC in server/config.py).
export const MIN_CROP_FRAC = 0.2;

export const FULL_FRAME = { x: 0, y: 0, w: 1, h: 1 };
export const UNEDITED = { rotate: 0, crop: null, mirror: false };

// A crop as it's drawn on the mirrored picture, or a crop drawn there as it's
// stored: mirroring flips x, so x = 1 - x - w both ways (to 1/10000, like dragCrop).
export function mirroredCrop(crop, mirror) {
  return mirror ? { ...crop, x: round4(1 - crop.x - crop.w) } : crop;
}

// How to show a `videoWidth` × `videoHeight` video framed by `framing`: the
// aspect ratio of what's left (for its wrapper, which hides the rest), and
// the video element's position, size and transform inside that wrapper, as
// fractions of it. The element is the whole frame, turned about its centre
// by `rotate` and then flipped by `mirror`, and placed so the crop exactly
// fills the wrapper.
export function framingStyle(framing, videoWidth, videoHeight) {
  const turned = framing.rotate % 180 !== 0;
  const frameWidth = turned ? videoHeight : videoWidth;   // after turning
  const frameHeight = turned ? videoWidth : videoHeight;
  const crop = mirroredCrop(framing.crop ?? FULL_FRAME, framing.mirror);
  const aspect = (crop.w * frameWidth) / (crop.h * frameHeight);
  // The frame shown is 1 / crop.w wrappers wide and 1 / crop.h high. Turned a
  // quarter, the element's own width is the frame's height, and vice versa.
  const width = turned ? 1 / (crop.h * aspect) : 1 / crop.w;
  const height = turned ? aspect / crop.w : 1 / crop.h;
  const centreX = (0.5 - crop.x) / crop.w;
  const centreY = (0.5 - crop.y) / crop.h;
  return {
    aspect,
    video: {
      left: percent(centreX - width / 2),
      top: percent(centreY - height / 2),
      width: percent(width),
      height: percent(height),
      transform: `${framing.mirror ? "scaleX(-1) " : ""}rotate(${framing.rotate}deg)`,
    },
  };
}

// `crop` dragged by (dx, dy), fractions of the frame, by its body ("move")
// or a corner ("nw", "ne", "sw", "se"). It stays inside the frame and at
// least MIN_CROP_FRAC each way. Moves go in steps of 1/10000 of the frame,
// well under a pixel, so the values stay tidy and the bounds exact.
export function dragCrop(crop, handle, dx, dy) {
  dx = round4(dx);
  dy = round4(dy);
  if (handle === "move") {
    return roundCrop({ ...crop, x: clamp(crop.x + dx, 0, 1 - crop.w), y: clamp(crop.y + dy, 0, 1 - crop.h) });
  }
  let left = crop.x;
  let right = crop.x + crop.w;
  let top = crop.y;
  let bottom = crop.y + crop.h;
  if (handle.includes("w")) left = clamp(left + dx, 0, right - MIN_CROP_FRAC);
  if (handle.includes("e")) right = clamp(right + dx, left + MIN_CROP_FRAC, 1);
  if (handle.includes("n")) top = clamp(top + dy, 0, bottom - MIN_CROP_FRAC);
  if (handle.includes("s")) bottom = clamp(bottom + dy, top + MIN_CROP_FRAC, 1);
  return roundCrop({ x: left, y: top, w: right - left, h: bottom - top });
}

// A quarter turn clockwise. The crop was a part of the old picture, so it goes.
export function rotateFraming(framing) {
  return { ...framing, rotate: (framing.rotate + 90) % 360, crop: null };
}

// "Set start here" at clip time `sec`, in a take `durationSec` long. The end
// stays if it's still after the new start. A trim with nothing left in it
// leaves `trim` as it was.
export function trimFromHere(trim, sec, durationSec) {
  const endSec = trim && trim.end_sec > sec ? trim.end_sec : durationSec;
  return validTrim({ start_sec: roundMs(sec), end_sec: endSec }) ?? trim;
}

// "Set end here" at clip time `sec`. The start stays if it's still before it.
export function trimToHere(trim, sec) {
  const startSec = trim && trim.start_sec < sec ? trim.start_sec : 0;
  return validTrim({ start_sec: startSec, end_sec: roundMs(sec) }) ?? trim;
}

// A short hash of the saved edits to both videos, for the /synced URL: it
// changes whenever an edit does, so the browser never replays a download
// made before it (invariant 7). The server names its file with a hash of its
// own (server/models.py's edits_key); the two needn't match. FNV-1a, since
// the browser's SHA-256 is async and missing outside HTTPS.
export function editsKey(song, clip) {
  const text = JSON.stringify([song.framing, clip.framing, clip.trim ?? null]);
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    hash = Math.imul(hash ^ text.charCodeAt(i), 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}

function validTrim(trim) {
  return trim.start_sec < trim.end_sec ? trim : null;
}

// Sums of 1/10000 steps, cleared of float noise.
function roundCrop(crop) {
  return { x: round4(crop.x), y: round4(crop.y), w: round4(crop.w), h: round4(crop.h) };
}

function round4(value) {
  return Math.round(value * 10000) / 10000;
}

function roundMs(sec) {
  return Math.round(sec * 1000) / 1000;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function percent(fraction) {
  return `${fraction * 100}%`;
}
