import { describe, expect, test } from "vitest";
import { RENDER_PARAM_FIELDS, syncedVideoUrl } from "./api.js";

const PARAMS = { reference_id: "ref", rate: 0.75, offset_sec: 12.25, layout: "take", sound: "song" };

describe("synced video URL", () => {
  test("names the clip in the path and every render param in the query", () => {
    const url = new URL(syncedVideoUrl("clip", PARAMS), "http://localhost");
    expect(url.pathname).toBe("/api/clips/clip/synced");
    expect([...url.searchParams.keys()]).toEqual(RENDER_PARAM_FIELDS);
    expect(Object.fromEntries(url.searchParams)).toEqual({
      reference_id: "ref", rate: "0.75", offset_sec: "12.25", layout: "take", sound: "song",
    });
  });

  test("changes when any render param changes", () => {
    for (const field of RENDER_PARAM_FIELDS) {
      const changed = { ...PARAMS, [field]: `${PARAMS[field]}-changed` };
      expect(syncedVideoUrl("clip", changed)).not.toBe(syncedVideoUrl("clip", PARAMS));
    }
  });

  test("refuses to build a URL with a param missing", () => {
    const { offset_sec, ...missingOffset } = PARAMS;
    expect(() => syncedVideoUrl("clip", missingOffset)).toThrow(/offset_sec/);
  });
});
