import { useEffect } from "react";
import { formatPreciseTime, formatTunedRate, nudgeAlignment, offsetNudgeForKey } from "../tuning.js";

// Tuning a take's alignment by hand, under the player. Every nudge goes to
// `onChange` and plays at once; Done saves, Cancel drops the changes, and
// Reset goes back to the matcher's alignment. On a keyboard, ← and → nudge
// the offset by 10 ms (100 ms with Shift).
export default function FineTune({ alignment, saving, onChange, onReset, onCancel, onDone }) {
  function nudge(offsetMs, rateSteps) {
    onChange(nudgeAlignment(alignment, offsetMs, rateSteps));
  }

  useEffect(() => {
    function onKeyDown(event) {
      // The scrubber and the segmented controls use the arrow keys themselves.
      if (event.target.closest("input, [role=radio]")) return;
      const offsetMs = offsetNudgeForKey(event.key, event.shiftKey);
      if (offsetMs === null) return;
      event.preventDefault();
      onChange(nudgeAlignment(alignment, offsetMs, 0));
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [alignment, onChange]);

  return (
    <section className="fine-tune" aria-label="Fine-tune">
      <div className="tune-row">
        <span className="hint tune-label">Offset</span>
        <OffsetButton ms={-100} onNudge={nudge} />
        <OffsetButton ms={-10} onNudge={nudge} />
        <output className="tune-value" aria-label="Where the take starts in the song">
          {formatPreciseTime(alignment.offset_sec)}
        </output>
        <OffsetButton ms={10} onNudge={nudge} />
        <OffsetButton ms={100} onNudge={nudge} />
      </div>
      <div className="tune-row">
        <span className="hint tune-label">Practice speed</span>
        <button className="button small" aria-label="Slower by 0.005" onClick={() => nudge(0, -1)}>−</button>
        <output className="tune-value" aria-label="Practice speed">{formatTunedRate(alignment.rate)}</output>
        <button className="button small" aria-label="Faster by 0.005" onClick={() => nudge(0, 1)}>+</button>
      </div>
      <p className="hint">
        A little early or late the whole way through? Move the offset. In sync at the start but drifting by the
        end? Change the practice speed. Pick Both under Sound to hear the song and the room together: they sound
        like one when they line up.
      </p>
      <div className="tune-actions">
        <button className="link" onClick={onReset}>Reset to automatic</button>
        <button className="button small" onClick={onCancel}>Cancel</button>
        <button className="button small primary" onClick={onDone} disabled={saving}>
          {saving ? "Saving…" : "Done"}
        </button>
      </div>
    </section>
  );
}

function OffsetButton({ ms, onNudge }) {
  const label = `${ms > 0 ? "+" : "−"}${Math.abs(ms)}`;
  return (
    <button className="button small" aria-label={`Offset ${label} milliseconds`} onClick={() => onNudge(ms, 0)}>
      {label}
    </button>
  );
}
