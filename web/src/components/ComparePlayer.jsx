import { useRef, useState } from "react";
import { REVIEW_SPEEDS, outputTimeFor } from "../flow.js";
import LayoutToggle from "./LayoutToggle.jsx";
import PlayBar from "./PlayBar.jsx";
import Segmented from "./Segmented.jsx";
import SoundToggle from "./SoundToggle.jsx";
import useLinkedPlayback from "./useLinkedPlayback.js";

// The synced take with the original choreography beside it or above it
// (`layout`), both cut to the same stretch of the song and driven by one play
// bar. The song plays from the reference element and the room from the take,
// so switching sound just flips which one is muted. When the song file is
// audio-only there's no picture to show, so the reference stays hidden (still
// playing the song), and there's no layout to pick.
//
// `takeRate` re-times the take live (flow.takeRateFor), so a tuned rate or
// offset plays at once without a new render. While `tuning`, Sound also
// offers Both.
//
// Speed slows both down together for reviewing a fast passage. It starts at
// 1× for every take and isn't saved.
const SPEED_OPTIONS = REVIEW_SPEEDS.map((speed) => ({ value: speed, label: `${speed}×` }));

export default function ComparePlayer({
  referenceUrl,
  takeUrl,
  offsetSec,
  takeRate,
  sound,
  tuning,
  onSoundChange,
  onReferenceVideo,
  layout,
  onLayoutChange,
}) {
  const takeRef = useRef(null);
  const referenceRef = useRef(null);
  const [takeMediaSec, setTakeMediaSec] = useState(0);
  const [takeAspect, setTakeAspect] = useState(null);
  const [referenceAspect, setReferenceAspect] = useState(null);   // null = no picture
  const [speed, setSpeed] = useState(1);
  const linked = useLinkedPlayback(takeRef, referenceRef, { offsetSec, takeRate, speed, sound });

  function takeLoaded() {
    const take = takeRef.current;
    setTakeMediaSec(take.duration);
    setTakeAspect(take.videoWidth / take.videoHeight);
  }

  function referenceLoaded() {
    const reference = referenceRef.current;
    const hasVideo = reference.videoWidth > 0;
    setReferenceAspect(hasVideo ? reference.videoWidth / reference.videoHeight : null);
    onReferenceVideo(hasVideo);
    linked.realign();
  }

  const hasReferenceVideo = referenceAspect !== null;
  return (
    <div className={`player ${layout}`}>
      <div className={`compare ${layout}`}>
        <video
          ref={referenceRef}
          className="compare-video"
          src={referenceUrl}
          playsInline
          preload="auto"
          hidden={layout === "take"}
          style={{ "--aspect": referenceAspect }}
          onLoadedMetadata={referenceLoaded}
          onTimeUpdate={linked.onTimeUpdate}
        />
        <video
          ref={takeRef}
          className="compare-video take"
          src={takeUrl}
          playsInline
          preload="auto"
          style={{ "--aspect": takeAspect }}
          onLoadedMetadata={takeLoaded}
          onTimeUpdate={linked.onTimeUpdate}
          onEnded={linked.pause}
        />
      </div>
      <PlayBar
        playing={linked.playing}
        currentSec={linked.currentSec}
        durationSec={outputTimeFor(takeMediaSec, takeRate)}
        onToggle={linked.playing ? linked.pause : linked.play}
        onSeek={linked.seek}
      />
      <div className="controls">
        <SoundToggle sound={sound} withBoth={tuning} onChange={onSoundChange} />
        <Segmented label="Speed" options={SPEED_OPTIONS} value={speed} onChange={setSpeed} />
        {hasReferenceVideo && <LayoutToggle layout={layout} onChange={onLayoutChange} />}
      </div>
    </div>
  );
}
