import { describe, expect, test } from "vitest";
import {
  alignmentSummary,
  formatPreciseTime,
  formatTunedRate,
  nudgeAlignment,
  offsetNudgeForKey,
} from "./tuning.js";

const AUTOMATIC = { rate: 0.75, offset_sec: 65.23, score: 9, peak_ratio: 1.5 };

function clipWith(manual) {
  return { alignment: { top_candidates: [AUTOMATIC], ambiguous: false, selected_index: null, manual } };
}

describe("nudging an alignment", () => {
  test("a take 150 ms late is fixed with one -100 tap and five -10 taps", () => {
    let alignment = { rate: 0.75, offset_sec: 65.23 };
    alignment = nudgeAlignment(alignment, -100, 0);
    alignment = nudgeAlignment(alignment, -10, 0);
    alignment = nudgeAlignment(alignment, -10, 0);
    alignment = nudgeAlignment(alignment, -10, 0);
    alignment = nudgeAlignment(alignment, -10, 0);
    alignment = nudgeAlignment(alignment, -10, 0);
    expect(alignment).toEqual({ rate: 0.75, offset_sec: 65.08 });
  });

  test("a hundred 10 ms nudges add up to exactly one second", () => {
    let alignment = { rate: 0.75, offset_sec: 0.1 };
    for (let i = 0; i < 100; i++) alignment = nudgeAlignment(alignment, 10, 0);
    expect(alignment.offset_sec).toBe(1.1);
  });

  test("rate steps are 0.005 and land on exact thousandths", () => {
    expect(nudgeAlignment({ rate: 0.75, offset_sec: 1 }, 0, 1).rate).toBe(0.755);
    let alignment = { rate: 0.75, offset_sec: 1 };
    for (let i = 0; i < 10; i++) alignment = nudgeAlignment(alignment, 0, 1);
    expect(alignment.rate).toBe(0.8);   // a take filmed at 0.8×, reached from 0.75
  });

  test("the rate stays inside what the server accepts", () => {
    expect(nudgeAlignment({ rate: 1, offset_sec: 1 }, 0, 1).rate).toBe(1);
    expect(nudgeAlignment({ rate: 0.25, offset_sec: 1 }, 0, -1).rate).toBe(0.25);
  });
});

describe("tuning keys", () => {
  test("arrows nudge 10 ms, or 100 ms with Shift", () => {
    expect(offsetNudgeForKey("ArrowLeft", false)).toBe(-10);
    expect(offsetNudgeForKey("ArrowRight", false)).toBe(10);
    expect(offsetNudgeForKey("ArrowRight", true)).toBe(100);
    expect(offsetNudgeForKey("ArrowUp", false)).toBeNull();
  });
});

describe("formatting tuned values", () => {
  test("offsets show hundredths of a second", () => {
    expect(formatPreciseTime(65.234)).toBe("1:05.23");
    expect(formatPreciseTime(59.999)).toBe("1:00.00");
    expect(formatPreciseTime(-2)).toBe("-0:02.00");
    expect(formatPreciseTime(0.004)).toBe("0:00.00");
  });

  test("rates show thousandths", () => {
    expect(formatTunedRate(0.75)).toBe("0.750×");
    expect(formatTunedRate(0.805)).toBe("0.805×");
  });

  test("the caption says when the alignment was adjusted by hand", () => {
    expect(alignmentSummary(clipWith(null))).toBe("Matched at 1:05 · 0.75× speed");
    expect(alignmentSummary(clipWith({ rate: 0.8, offset_sec: 65.08 }))).toBe(
      "Adjusted by hand · 1:05.08 · 0.800× speed",
    );
  });
});
