import { useRef, useState } from "react";
import { REVIEW_SPEEDS, playbackRates } from "../flow.js";
import LayoutToggle from "./LayoutToggle.jsx";
import PlayBar from "./PlayBar.jsx";
import Segmented from "./Segmented.jsx";
import SoundToggle from "./SoundToggle.jsx";
import useLinkedPlayback from "./useLinkedPlayback.js";

// The synced take with the original choreography beside it or above it
// (`layout`), both cut to the same stretch of the song and driven by one play
// bar. Only the take makes sound; the reference is always muted. When the
// song file is audio-only there's no picture to show, so the reference stays
// hidden, the take plays alone, and there's no layout to pick.
//
// Speed slows both down together for reviewing a fast passage. It starts at
// 1× for every take and isn't saved.
const SPEED_OPTIONS = REVIEW_SPEEDS.map((speed) => ({ value: speed, label: `${speed}×` }));

export default function ComparePlayer({
  referenceUrl,
  takeUrl,
  offsetSec,
  sound,
  roomAvailable,
  onSoundChange,
  onReferenceVideo,
  layout,
  onLayoutChange,
}) {
  const takeRef = useRef(null);
  const referenceRef = useRef(null);
  const resumeRef = useRef(null);   // where to pick up after switching sound
  const [durationSec, setDurationSec] = useState(0);
  const [takeAspect, setTakeAspect] = useState(null);
  const [referenceAspect, setReferenceAspect] = useState(null);   // null = no picture
  const [speed, setSpeed] = useState(1);
  // The take here is a render, so it's already at the song's tempo.
  const rates = playbackRates({ rate: 1, speed });
  const linked = useLinkedPlayback(takeRef, referenceRef, offsetSec, rates);

  function takeLoaded() {
    const take = takeRef.current;
    setDurationSec(take.duration);
    setTakeAspect(take.videoWidth / take.videoHeight);
    const resume = resumeRef.current;
    resumeRef.current = null;
    if (resume === null) return;
    linked.seek(resume.sec);
    if (resume.playing) linked.play();
  }

  function referenceLoaded() {
    const reference = referenceRef.current;
    const hasVideo = reference.videoWidth > 0;
    setReferenceAspect(hasVideo ? reference.videoWidth / reference.videoHeight : null);
    onReferenceVideo(hasVideo);
    linked.alignReference();
  }

  // Each sound is its own render, so switching swaps the take's source.
  // Remember the position first; `takeLoaded` restores it on the new source.
  function changeSound(nextSound) {
    if (nextSound === sound) return;
    resumeRef.current = { sec: takeRef.current.currentTime, playing: linked.playing };
    linked.pause();
    onSoundChange(nextSound);
  }

  const hasReferenceVideo = referenceAspect !== null;
  return (
    <div className={`player ${layout}`}>
      <div className={`compare ${layout}`}>
        <video
          ref={referenceRef}
          className="compare-video"
          src={referenceUrl}
          muted
          playsInline
          preload="auto"
          hidden={layout === "take"}
          style={{ "--aspect": referenceAspect }}
          onLoadedMetadata={referenceLoaded}
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
        durationSec={durationSec}
        onToggle={linked.playing ? linked.pause : linked.play}
        onSeek={linked.seek}
      />
      <div className="controls">
        <SoundToggle sound={sound} roomAvailable={roomAvailable} onChange={changeSound} />
        <Segmented label="Speed" options={SPEED_OPTIONS} value={speed} onChange={setSpeed} />
        {hasReferenceVideo && <LayoutToggle layout={layout} onChange={onLayoutChange} />}
      </div>
    </div>
  );
}
