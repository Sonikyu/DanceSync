import { describe, expect, test } from "vitest";
import {
  FULL_FRAME,
  MIN_CROP_FRAC,
  UNEDITED,
  dragCrop,
  editsKey,
  framingStyle,
  mirroredCrop,
  rotateFraming,
  trimFromHere,
  trimToHere,
} from "./editing.js";

// Where pixel (u, v) of the video (fractions of its own frame) ends up in
// the wrapper, as fractions of it, if the browser lays it out with `style`:
// the element's box, then its transform about its centre (rotate, then the
// mirror's scaleX(-1)). The wrapper is drawn 1000 px wide.
function shownAt(style, u, v) {
  const wrapperWidth = 1000;
  const wrapperHeight = wrapperWidth / style.aspect;
  const { left, top, width, height, transform } = style.video;
  const box = {
    width: (parseFloat(width) / 100) * wrapperWidth,
    height: (parseFloat(height) / 100) * wrapperHeight,
  };
  const centreX = (parseFloat(left) / 100) * wrapperWidth + box.width / 2;
  const centreY = (parseFloat(top) / 100) * wrapperHeight + box.height / 2;
  const angle = (Number(transform.match(/rotate\((\d+)deg\)/)[1]) * Math.PI) / 180;
  const x = (u - 0.5) * box.width;
  const y = (v - 0.5) * box.height;
  let turnedX = x * Math.cos(angle) - y * Math.sin(angle);
  const turnedY = x * Math.sin(angle) + y * Math.cos(angle);
  if (transform.includes("scaleX(-1)")) turnedX = -turnedX;
  return [(centreX + turnedX) / wrapperWidth, (centreY + turnedY) / wrapperHeight];
}

// Where ffmpeg puts the same pixel (dancesync/framing.py): turned clockwise,
// cropped, then mirrored.
function renderedAt(framing, u, v) {
  const turned = { 0: [u, v], 90: [1 - v, u], 180: [1 - u, 1 - v], 270: [v, 1 - u] }[framing.rotate];
  const crop = framing.crop ?? FULL_FRAME;
  const x = (turned[0] - crop.x) / crop.w;
  const y = (turned[1] - crop.y) / crop.h;
  return [framing.mirror ? 1 - x : x, y];
}

const CROP = { x: 0.1, y: 0.3, w: 0.4, h: 0.5 };
const POINTS = [[0, 0], [1, 0], [0, 1], [0.25, 0.75], [0.6, 0.45]];

describe("framing preview", () => {
  test("unedited, the video fills its wrapper at its own shape", () => {
    expect(framingStyle(UNEDITED, 1920, 1080)).toEqual({
      aspect: 1920 / 1080,
      video: { left: "0%", top: "0%", width: "100%", height: "100%", transform: "rotate(0deg)" },
    });
  });

  test("a crop's wrapper has the crop's shape in pixels", () => {
    // Half the width and all the height of a 1920x1080 frame is 960x1080.
    expect(framingStyle({ ...UNEDITED, crop: { x: 0.25, y: 0, w: 0.5, h: 1 } }, 1920, 1080).aspect).toBe(960 / 1080);
  });

  test("a quarter turn makes a landscape video portrait", () => {
    expect(framingStyle({ ...UNEDITED, rotate: 90 }, 1920, 1080).aspect).toBe(1080 / 1920);
    expect(framingStyle({ ...UNEDITED, rotate: 180 }, 1920, 1080).aspect).toBe(1920 / 1080);
  });

  const FRAMINGS = [];
  for (const rotate of [0, 90, 180, 270]) {
    for (const crop of [null, CROP]) {
      for (const mirror of [false, true]) FRAMINGS.push({ rotate, crop, mirror });
    }
  }

  test.each(FRAMINGS)("shows every pixel where the render puts it: %o", (framing) => {
    const style = framingStyle(framing, 1280, 720);
    for (const [u, v] of POINTS) {
      const [shownX, shownY] = shownAt(style, u, v);
      const [renderedX, renderedY] = renderedAt(framing, u, v);
      expect(shownX).toBeCloseTo(renderedX, 9);
      expect(shownY).toBeCloseTo(renderedY, 9);
    }
  });
});

describe("crop editing", () => {
  test("a crop drawn on the mirrored picture is stored flipped, and back", () => {
    expect(mirroredCrop(CROP, true)).toEqual({ ...CROP, x: 0.5 });
    expect(mirroredCrop(mirroredCrop(CROP, true), true)).toEqual(CROP);
    expect(mirroredCrop(CROP, false)).toBe(CROP);
  });

  test("a crop drawn on the left of the mirrored picture keeps the same dancer when mirror is turned off", () => {
    // The dancer drawn around on screen, mirrored, at the left edge…
    const drawn = { x: 0, y: 0, w: 0.3, h: 1 };
    const stored = mirroredCrop(drawn, true);
    // …stands at the right edge of the picture as filmed.
    expect(stored.x).toBeCloseTo(0.7, 12);
    expect(renderedAt({ rotate: 0, crop: stored, mirror: true }, 0.85, 0.5)[0]).toBeCloseTo(0.5, 12);
  });

  test("moving keeps the whole crop inside the frame", () => {
    expect(dragCrop(CROP, "move", 0.1, -0.1)).toEqual({ ...CROP, x: 0.2, y: 0.2 });
    expect(dragCrop(CROP, "move", 0.9, 0.9)).toEqual({ ...CROP, x: 0.6, y: 0.5 });
    expect(dragCrop(CROP, "move", -0.9, -0.9)).toEqual({ ...CROP, x: 0, y: 0 });
  });

  test("a corner moves its two edges, and the opposite corner stays put", () => {
    expect(dragCrop(CROP, "se", 0.1, 0.1)).toEqual({ x: 0.1, y: 0.3, w: 0.5, h: 0.6 });
    expect(dragCrop(CROP, "nw", -0.1, 0.1)).toEqual({ x: 0, y: 0.4, w: 0.5, h: 0.4 });
    expect(dragCrop(CROP, "ne", 0.7, -0.5)).toEqual({ x: 0.1, y: 0, w: 0.9, h: 0.8 });
  });

  test("a crop never shrinks below MIN_CROP_FRAC or leaves the frame", () => {
    for (const handle of ["nw", "ne", "sw", "se"]) {
      for (const [dx, dy] of [[1, 1], [-1, -1], [1, -1], [-1, 1], [0.123456, -0.654321]]) {
        const crop = dragCrop(CROP, handle, dx, dy);
        expect(crop.w).toBeGreaterThanOrEqual(MIN_CROP_FRAC);
        expect(crop.h).toBeGreaterThanOrEqual(MIN_CROP_FRAC);
        expect(Math.min(crop.x, crop.y)).toBeGreaterThanOrEqual(0);
        expect(crop.x + crop.w).toBeLessThanOrEqual(1 + 1e-9);
        expect(crop.y + crop.h).toBeLessThanOrEqual(1 + 1e-9);
      }
    }
  });

  test("rotating turns a quarter clockwise and drops the crop", () => {
    expect(rotateFraming({ rotate: 270, crop: CROP, mirror: true })).toEqual({ rotate: 0, crop: null, mirror: true });
    expect(rotateFraming(UNEDITED).rotate).toBe(90);
  });
});

describe("trim", () => {
  test("set start here keeps the end when it's still after the start", () => {
    expect(trimFromHere(null, 2.5, 30)).toEqual({ start_sec: 2.5, end_sec: 30 });
    expect(trimFromHere({ start_sec: 1, end_sec: 20 }, 4.1234, 30)).toEqual({ start_sec: 4.123, end_sec: 20 });
    expect(trimFromHere({ start_sec: 1, end_sec: 20 }, 25, 30)).toEqual({ start_sec: 25, end_sec: 30 });
  });

  test("set end here keeps the start when it's still before the end", () => {
    expect(trimToHere(null, 20)).toEqual({ start_sec: 0, end_sec: 20 });
    expect(trimToHere({ start_sec: 2, end_sec: 30 }, 20)).toEqual({ start_sec: 2, end_sec: 20 });
    expect(trimToHere({ start_sec: 25, end_sec: 30 }, 20)).toEqual({ start_sec: 0, end_sec: 20 });
  });

  test("a trim with nothing left in it changes nothing", () => {
    const trim = { start_sec: 2, end_sec: 20 };
    expect(trimFromHere(trim, 30, 30)).toBe(trim);
    expect(trimToHere(trim, 0)).toBe(trim);
  });
});

describe("edits key", () => {
  const song = { framing: UNEDITED };
  const clip = { framing: UNEDITED, trim: null };

  test("is a short hex hash that only changes with the edits", () => {
    expect(editsKey(song, clip)).toMatch(/^[0-9a-f]{8}$/);
    expect(editsKey({ ...song }, { ...clip })).toBe(editsKey(song, clip));
    expect(editsKey(song, { ...clip, trim: { start_sec: 1, end_sec: 2 } })).not.toBe(editsKey(song, clip));
    expect(editsKey({ framing: { ...UNEDITED, mirror: true } }, clip)).not.toBe(editsKey(song, clip));
  });
});
