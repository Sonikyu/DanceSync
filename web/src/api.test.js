import { afterEach, describe, expect, test, vi } from "vitest";
import { RENDER_PARAM_FIELDS, importReference, syncedVideoUrl } from "./api.js";

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

describe("YouTube import", () => {
  afterEach(() => vi.unstubAllGlobals());

  function respondWith(status, body) {
    const fetch = vi.fn(async () => new Response(JSON.stringify(body), { status }));
    vi.stubGlobal("fetch", fetch);
    return fetch;
  }

  test("posts the link and resolves to the reference", async () => {
    const fetch = respondWith(201, { id: "ref", filename: "Practice.mp4" });
    await expect(importReference("https://youtu.be/abcDEF12345")).resolves.toEqual({ id: "ref", filename: "Practice.mp4" });
    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe("/api/references/import");
    expect(JSON.parse(options.body)).toEqual({ url: "https://youtu.be/abcDEF12345" });
  });

  test.each([
    [400, /not a link to a YouTube video/],
    [413, /under 15 minutes/],
    [422, /private, age-restricted, or live/],
    [503, /isn't set up on this server/],
  ])("explains a %i in import terms", async (status, message) => {
    respondWith(status, { detail: "server text" });
    await expect(importReference("https://youtu.be/x")).rejects.toThrow(message);
  });
});
