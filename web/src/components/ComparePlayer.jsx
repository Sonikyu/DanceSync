import { useRef, useState } from "react";
import PlayBar from "./PlayBar.jsx";
import SoundToggle from "./SoundToggle.jsx";
import useLinkedPlayback from "./useLinkedPlayback.js";

// The synced take beside the original choreography, both cut to the same
// stretch of the song and driven by one play bar. Only the take makes sound;
// the reference is always muted. When the song file is audio-only there's no
// picture to show, so the reference stays hidden and the take plays alone.
export default function ComparePlayer({
  referenceUrl,
  takeUrl,
  offsetSec,
  sound,
  roomAvailable,
  onSoundChange,
  onReferenceVideo,
}) {
  const takeRef = useRef(null);
  const referenceRef = useRef(null);
  const resumeRef = useRef(null);   // where to pick up after switching sound
  const [durationSec, setDurationSec] = useState(0);
  const [takeAspect, setTakeAspect] = useState(null);
  const [referenceAspect, setReferenceAspect] = useState(null);   // null = no picture
  const linked = useLinkedPlayback(takeRef, referenceRef, offsetSec);

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

  const showReference = referenceAspect !== null;
  return (
    <div className={showReference ? "player wide" : "player"}>
      <div className="compare">
        <video
          ref={referenceRef}
          className="compare-video"
          src={referenceUrl}
          muted
          playsInline
          preload="auto"
          hidden={!showReference}
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
      <SoundToggle sound={sound} roomAvailable={roomAvailable} onChange={changeSound} />
    </div>
  );
}
