import { formatTime, timelinePercent } from "../flow.js";

// The whole song as one bar, with a numbered marker where each candidate
// starts. Purely visual -- the candidate cards below carry the controls.
export default function SongTimeline({ durationSec, candidates, playingIndex }) {
  return (
    <div aria-hidden="true">
      <div className="timeline">
        <div className="timeline-track" />
        {candidates.map((candidate, index) => (
          <span
            key={index}
            className={index === playingIndex ? "timeline-marker active" : "timeline-marker"}
            style={{ left: `${timelinePercent(candidate.offset_sec, durationSec)}%` }}
          >
            {index + 1}
          </span>
        ))}
      </div>
      <div className="timeline-ends">
        <span>0:00</span>
        <span>{formatTime(durationSec)}</span>
      </div>
    </div>
  );
}
