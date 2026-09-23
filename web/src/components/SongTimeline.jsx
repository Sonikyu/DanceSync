import { formatTime, timelinePercent } from "../flow.js";

// The whole song as one bar, with a numbered marker where each candidate
// starts. On the Match step it's purely visual -- the candidate cards carry
// the controls. With `onPick`, the one marker can be dragged along the song
// (or moved with the arrow keys), for placing a take by hand; `onPick` gets
// the new position in song seconds.
export default function SongTimeline({ durationSec, candidates, playingIndex, onPick }) {
  return (
    <div aria-hidden={onPick ? undefined : "true"}>
      <div className="timeline">
        <div className="timeline-track" />
        {candidates.map((candidate, index) => (
          <span
            key={index}
            className={index === playingIndex ? "timeline-marker active" : "timeline-marker"}
            style={{ left: `${timelinePercent(candidate.offset_sec, durationSec)}%` }}
          >
            {onPick ? "" : index + 1}
          </span>
        ))}
        {onPick && (
          <input
            className="timeline-input"
            type="range"
            aria-label="Where your take starts in the song"
            aria-valuetext={formatTime(candidates[0].offset_sec)}
            min={0}
            max={durationSec}
            step={0.1}
            value={candidates[0].offset_sec}
            onChange={(event) => onPick(Number(event.target.value))}
          />
        )}
      </div>
      <div className="timeline-ends">
        <span>0:00</span>
        <span>{formatTime(durationSec)}</span>
      </div>
    </div>
  );
}
