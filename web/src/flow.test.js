import { describe, expect, test } from "vitest";
import {
  chosenCandidate,
  clipTooShortMessage,
  formatRate,
  formatTime,
  referenceTimeFor,
  songTitle,
  stageOf,
  stepAfterAlignment,
  strengthLabel,
  timelinePercent,
} from "./flow.js";

const CANDIDATES = [
  { rate: 0.75, offset_sec: 72.0, score: 0.8, peak_ratio: 1.02 },
  { rate: 0.75, offset_sec: 132.0, score: 0.76, peak_ratio: 0.98 },
  { rate: 1.0, offset_sec: 12.5, score: 0.4, peak_ratio: 0.5 },
];

function clipWith(alignment) {
  return {
    alignment: { top_candidates: CANDIDATES, ambiguous: false, selected_index: null, ...alignment },
  };
}

describe("step flow", () => {
  test("an ambiguous match stops at the match step", () => {
    expect(stepAfterAlignment(clipWith({ ambiguous: true }))).toBe("match");
  });

  test("a clear match goes straight to watching", () => {
    expect(stepAfterAlignment(clipWith({ ambiguous: false }))).toBe("watch");
  });

  test("a failed match says so instead of asking which candidate", () => {
    expect(stepAfterAlignment(clipWith({ failed: true, ambiguous: true }))).toBe("nomatch");
    expect(stepAfterAlignment(clipWith({ failed: false }))).toBe("watch");
  });

  test("no match stands in for the watch stage", () => {
    expect(stageOf("nomatch")).toBe(stageOf("watch"));
  });

  test("a too-short clip is told its length and the minimum", () => {
    expect(clipTooShortMessage(5.96, 10)).toMatch(/^That video is 6 seconds long\. A take needs at least 10 seconds/);
    expect(clipTooShortMessage(0.4, 10)).toMatch(/^That video is 1 second long\./);
  });

  test("the match step shares the video stage's dot", () => {
    expect(stageOf("match")).toBe(stageOf("video"));
    expect(stageOf("watch")).toBe(2);
  });

  test("the reference runs offset seconds ahead of the take", () => {
    expect(referenceTimeFor(5, 62)).toBe(67);
  });

  test("the reference has no time until a late-starting song begins", () => {
    expect(referenceTimeFor(0.5, -1.5)).toBeNull();
    expect(referenceTimeFor(2, -1.5)).toBe(0.5);
  });

  test("the chosen candidate defaults to the matcher's best", () => {
    expect(chosenCandidate(clipWith({}))).toBe(CANDIDATES[0]);
    expect(chosenCandidate(clipWith({ selected_index: 2 }))).toBe(CANDIDATES[2]);
  });
});

describe("formatting", () => {
  test.each([
    [0, "0:00"],
    [65.2, "1:05"],
    [59.6, "1:00"],
    [125, "2:05"],
    [-2.2, "-0:02"],
    [-0.3, "0:00"],
  ])("formatTime(%s) is %s", (sec, text) => {
    expect(formatTime(sec)).toBe(text);
  });

  test("rates read as speeds", () => {
    expect(formatRate(0.75)).toBe("0.75× speed");
    expect(formatRate(1)).toBe("full speed");
  });

  test("runners-up are described relative to the winner", () => {
    expect(strengthLabel(CANDIDATES, 0)).toBe("strongest match");
    expect(strengthLabel(CANDIDATES, 1)).toBe("95% as strong");
  });

  test("timeline positions clamp to the bar", () => {
    expect(timelinePercent(50, 200)).toBe(25);
    expect(timelinePercent(-3, 200)).toBe(0);
    expect(timelinePercent(250, 200)).toBe(100);
  });

  test("song titles drop the file extension", () => {
    expect(songTitle("Levitating.mp3")).toBe("Levitating");
    expect(songTitle("dance.practice.mp4")).toBe("dance.practice");
  });
});
