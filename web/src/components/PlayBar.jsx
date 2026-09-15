import { formatTime } from "../flow.js";
import { PauseIcon, PlayIcon } from "./icons.jsx";

export default function PlayBar({ playing, currentSec, durationSec, onToggle, onSeek }) {
  return (
    <div className="playbar">
      <button className="play" aria-label={playing ? "Pause" : "Play"} onClick={onToggle}>
        {playing ? <PauseIcon /> : <PlayIcon />}
      </button>
      <input
        className="scrubber"
        type="range"
        aria-label="Position"
        min={0}
        max={durationSec}
        step={0.01}
        value={currentSec}
        onChange={(event) => onSeek(Number(event.target.value))}
      />
      <span className="playbar-time">
        {formatTime(currentSec)} / {formatTime(durationSec)}
      </span>
    </div>
  );
}
