import { formatRate, formatTime, strengthLabel } from "../flow.js";
import { PauseIcon, PlayIcon } from "./icons.jsx";

export default function CandidateCard({ candidates, index, playing, onPlay, onPick }) {
  const candidate = candidates[index];
  const number = index + 1;
  return (
    <li className={playing ? "card active" : "card"}>
      <button className="play" aria-label={`${playing ? "Stop" : "Play"} match ${number}`} onClick={onPlay}>
        {playing ? <PauseIcon /> : <PlayIcon />}
      </button>
      <div className="card-body">
        <div className="card-title">
          <span className="card-number">{number}</span>
          {formatTime(candidate.offset_sec)}
        </div>
        <div className="card-meta">
          {formatRate(candidate.rate)} · {strengthLabel(candidates, index)}
        </div>
      </div>
      <button className="button small" onClick={onPick}>Use this</button>
    </li>
  );
}
