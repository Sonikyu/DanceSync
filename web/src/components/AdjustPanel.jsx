import { UNEDITED, rotateFraming, trimFromHere, trimToHere } from "../editing.js";
import { formatPreciseTime } from "../tuning.js";

// Adjusting one video's framing (and the take's trim), under the player.
// The crop box is drawn over the video itself (CropBox); this has the rest.
// Every change goes to `onChange` as { framing, trim } and shows at once;
// Done saves, Cancel drops the changes, and Reset clears every edit (saved
// on Done). Trim uses the play position, `clipSec` seconds into the take as
// filmed, which is easier on a phone than dragging two handles.
export default function AdjustPanel({ target, edit, clipSec, durationSec, saving, onChange, onCancel, onDone }) {
  const { framing, trim } = edit;
  const setFraming = (changed) => onChange({ ...edit, framing: changed });
  const setTrim = (changed) => onChange({ ...edit, trim: changed });

  return (
    <section className="fine-tune" aria-label={target === "take" ? "Adjust your take" : "Adjust the song's video"}>
      <p className="hint">
        Drag the box, or its corners, to crop to the dancer.
        {target === "take" && " Play or scrub to where the take should start or end, then set it."}
      </p>
      <div className="tune-row">
        <button className="button small" aria-pressed={framing.mirror} onClick={() => setFraming({ ...framing, mirror: !framing.mirror })}>
          {framing.mirror ? "Mirrored" : "Mirror"}
        </button>
        <button className="button small" onClick={() => setFraming(rotateFraming(framing))}>Rotate</button>
      </div>
      {target === "take" && (
        <div className="tune-row">
          <span className="hint tune-label">
            Starts at {formatPreciseTime(trim?.start_sec ?? 0)} · ends at {formatPreciseTime(trim?.end_sec ?? durationSec)}
          </span>
          <button className="button small" onClick={() => setTrim(trimFromHere(trim, clipSec, durationSec))}>
            Set start here
          </button>
          <button className="button small" onClick={() => setTrim(trimToHere(trim, clipSec))}>Set end here</button>
        </div>
      )}
      <div className="tune-actions">
        <button className="link" onClick={() => onChange({ framing: UNEDITED, trim: null })}>Reset</button>
        <button className="button small" onClick={onCancel}>Cancel</button>
        <button className="button small primary" onClick={onDone} disabled={saving}>
          {saving ? "Saving…" : "Done"}
        </button>
      </div>
    </section>
  );
}
