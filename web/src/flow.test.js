import { describe, expect, test } from "vitest";
import {
  chosenCandidate,
  clipTimeFor,
  clipTooShortMessage,
  formatRate,
  formatTime,
  leaderFor,
  nextOption,
  playbackRates,
  outputTimeFor,
  referenceTimeFor,
  renderParams,
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

describe("render params", () => {
  test("carry the chosen candidate's alignment and the requested render", () => {
    const clip = { reference_id: "ref", ...clipWith({ selected_index: 1 }) };
    expect(renderParams(clip, "room", "side-by-side")).toEqual({
      reference_id: "ref",
      rate: 0.75,
      offset_sec: 132.0,
      layout: "side-by-side",
      sound: "room",
    });
  });
});

describe("clip and output time", () => {
  const TIMES = [0, 0.1, 1 / 3, 7.2, 12.25, 59.9, 3600];

  test("a 0.75× take plays at 1.333×: 3 s of output shows clip second 4", () => {
    expect(clipTimeFor(3, 0.75)).toBe(4);
    expect(outputTimeFor(4, 0.75)).toBe(3);
    expect(clipTimeFor(3, 0.5)).toBe(6);
    expect(clipTimeFor(3, 1)).toBe(3);
  });

  test("round trips are exact at 1× and 0.5×", () => {
    for (const rate of [1, 0.5]) {
      for (const sec of TIMES) {
        expect(outputTimeFor(clipTimeFor(sec, rate), rate)).toBe(sec);
        expect(clipTimeFor(outputTimeFor(sec, rate), rate)).toBe(sec);
      }
    }
  });

  // Dividing by 0.75 can't be exact in binary floating point: some values
  // come back one unit in the last place off. A picosecond is not a frame.
  test("round trips at 0.75× agree to a picosecond", () => {
    for (const sec of TIMES) {
      expect(Math.abs(outputTimeFor(clipTimeFor(sec, 0.75), 0.75) - sec)).toBeLessThan(1e-12);
      expect(Math.abs(clipTimeFor(outputTimeFor(sec, 0.75), 0.75) - sec)).toBeLessThan(1e-12);
    }
  });

  test("with a negative offset, the song starts partway into the take", () => {
    // The phone started recording 2 s (of song time) before the song. The
    // song starts at output 2 s, which is clip second 2.667 of a 0.75× take.
    expect(referenceTimeFor(1, -2)).toBeNull();
    expect(referenceTimeFor(2, -2)).toBe(0);
    expect(clipTimeFor(2, 0.75)).toBeCloseTo(8 / 3, 12);
  });

  test("the element making the sound leads", () => {
    expect(leaderFor("song")).toBe("reference");
    expect(leaderFor("room")).toBe("take");
  });
});

describe("review speed", () => {
  test("a rendered take and the song both play at the review speed", () => {
    expect(playbackRates({ rate: 1, speed: 0.5 })).toEqual({ take: 0.5, reference: 0.5 });
    expect(playbackRates({ rate: 1, speed: 1 })).toEqual({ take: 1, reference: 1 });
  });

  test("the raw clip plays at speed / rate", () => {
    expect(playbackRates({ rate: 0.75, speed: 1 }).take).toBeCloseTo(4 / 3, 12);
    expect(playbackRates({ rate: 0.5, speed: 0.75 }).take).toBe(1.5);
  });

  test("reviewing at the practice speed plays the raw clip exactly as filmed", () => {
    for (const rate of [0.5, 0.75, 1]) {
      expect(playbackRates({ rate, speed: rate }).take).toBe(1);
    }
  });
});

describe("segmented control keys", () => {
  const OPTIONS = [{ value: "a" }, { value: "b", disabled: true }, { value: "c" }];

  test("arrows move to the next enabled option, wrapping around", () => {
    expect(nextOption(OPTIONS, "a", 1)).toBe("c");
    expect(nextOption(OPTIONS, "c", 1)).toBe("a");
    expect(nextOption(OPTIONS, "a", -1)).toBe("c");
    expect(nextOption(OPTIONS, "c", -1)).toBe("a");
  });

  test("with nothing else enabled there's nowhere to go", () => {
    expect(nextOption([{ value: "a" }, { value: "b", disabled: true }], "a", 1)).toBeNull();
  });

  test("numbers work as values", () => {
    expect(nextOption([{ value: 0.5 }, { value: 0.75 }, { value: 1 }], 0.75, 1)).toBe(1);
  });
});
