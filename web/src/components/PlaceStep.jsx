import { useState } from "react";
import { referenceMediaUrl, setManualAlignment } from "../api.js";
import { PRACTICE_RATES, formatPreciseTime } from "../tuning.js";
import Segmented from "./Segmented.jsx";
import SongTimeline from "./SongTimeline.jsx";
import useSongPreview from "./useSongPreview.js";

const RATE_OPTIONS = PRACTICE_RATES.map((rate) => ({ value: rate, label: rate === 1 ? "Full" : `${rate}×` }));

// When the matcher can't find a take, the dancer places it by hand: roughly
// where it starts in the song, and the speed they practised at. Watch then
// opens with the fine-tune panel, to get it exact by ear.
export default function PlaceStep({ song, clip, onBack, onPlaced }) {
  const [startSec, setStartSec] = useState(0);
  const [rate, setRate] = useState(0.75);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const preview = useSongPreview(referenceMediaUrl(song.id));

  function moveStart(sec) {
    preview.stop();
    setStartSec(sec);
  }

  async function place() {
    preview.stop();
    setSaving(true);
    try {
      onPlaced(await setManualAlignment(clip.id, { rate, offset_sec: startSec }));
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <section className="step">
      <button className="back" onClick={onBack}>← Back</button>
      <h1>Place your take by hand</h1>
      <p className="lede">Drag to about where your video starts in the song, then play a few seconds to check.</p>
      <SongTimeline
        durationSec={song.duration_sec}
        candidates={[{ offset_sec: startSec }]}
        playingIndex={preview.playingIndex}
        onPick={moveStart}
      />
      <div className="place-row">
        <output className="tune-value">{formatPreciseTime(startSec)}</output>
        <button className="button small" onClick={() => preview.toggle(0, startSec)}>
          {preview.playingIndex === 0 ? "Stop" : "Play from here"}
        </button>
      </div>
      <Segmented label="Practice speed" options={RATE_OPTIONS} value={rate} onChange={setRate} />
      <p className="hint">Close is enough: you'll fine-tune it by ear next.</p>
      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button className="button primary" onClick={place} disabled={saving}>
          {saving ? "Saving…" : "Continue"}
        </button>
      </div>
    </section>
  );
}
