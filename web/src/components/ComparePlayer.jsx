import { useRef, useState } from "react";
import { FULL_FRAME, framingStyle, mirroredCrop } from "../editing.js";
import { REVIEW_SPEEDS, clipTimeFor, outputTimeFor } from "../flow.js";
import AdjustPanel from "./AdjustPanel.jsx";
import LayoutToggle from "./LayoutToggle.jsx";
import PlayBar from "./PlayBar.jsx";
import Segmented from "./Segmented.jsx";
import SoundToggle from "./SoundToggle.jsx";
import useLinkedPlayback from "./useLinkedPlayback.js";
import VideoCell from "./VideoCell.jsx";

// The synced take with the original choreography beside it or above it
// (`layout`), both cut to the same stretch of the song and driven by one play
// bar. The song plays from the reference element and the room from the take,
// so switching sound just flips which one is muted. When the song file is
// audio-only there's no picture to show, so the reference stays hidden (still
// playing the song), and there's no layout to pick.
//
// The take is the raw clip, or a render of it where the browser can't play
// the raw clip (`onTakeUnplayable`). `takeRate` re-times it live
// (flow.takeRateFor), so a tuned rate or offset plays at once without a new
// render, and only the take media's `takeStartSec` to `takeEndSec` plays (a
// trim). While `tuning`, Sound also offers Both.
//
// Each video is shown in its framing (crop, mirror, rotate), with CSS that
// matches the render (editing.framingStyle). `onAdjust(target)` opens
// Adjust for "reference" or "take"; while `adjusting` one, it shows the
// whole picture under a crop box, and AdjustPanel below.
//
// Speed slows both down together for reviewing a fast passage. It starts at
// 1× for every take and isn't saved.
const SPEED_OPTIONS = REVIEW_SPEEDS.map((speed) => ({ value: speed, label: `${speed}×` }));

export default function ComparePlayer({
  referenceUrl,
  takeUrl,
  offsetSec,
  takeRate,
  takeStartSec,
  takeEndSec,
  referenceFraming,
  takeFraming,
  sound,
  tuning,
  onSoundChange,
  onReferenceVideo,
  onTakeUnplayable,
  layout,
  onLayoutChange,
  onAdjust,
  takeAdjustable,
  adjusting,
}) {
  const takeRef = useRef(null);
  const referenceRef = useRef(null);
  const [takeMediaSec, setTakeMediaSec] = useState(0);
  const [takeSize, setTakeSize] = useState(null);
  const [referenceSize, setReferenceSize] = useState(null);   // null = no picture
  const [speed, setSpeed] = useState(1);
  const timing = { offsetSec, takeRate, takeStartSec, takeEndSec, speed, sound };
  const linked = useLinkedPlayback(takeRef, referenceRef, timing);

  // A browser that can't decode the picture may still play the sound, with
  // no picture and no error (Chrome with an HEVC clip), so that counts as
  // unplayable too.
  function takeLoaded() {
    const take = takeRef.current;
    if (take.videoWidth === 0) {
      onTakeUnplayable();
      return;
    }
    setTakeMediaSec(take.duration);
    setTakeSize({ width: take.videoWidth, height: take.videoHeight });
    linked.realign();   // to the trim's start
  }

  function referenceLoaded() {
    const reference = referenceRef.current;
    const hasVideo = reference.videoWidth > 0;
    setReferenceSize(hasVideo ? { width: reference.videoWidth, height: reference.videoHeight } : null);
    onReferenceVideo(hasVideo);
    linked.realign();
  }

  function adjust(target) {
    linked.pause();
    onAdjust(target);
  }

  // The crop box is drawn on the picture as shown, mirrored or not.
  function changeCrop(framing, shownCrop) {
    const crop = mirroredCrop(shownCrop, framing.mirror);
    adjusting.onChange({ ...adjusting.edit, framing: { ...framing, crop } });
  }

  const reference = framed(referenceFraming, referenceSize, adjusting?.target === "reference");
  const take = framed(takeFraming, takeSize, adjusting?.target === "take");
  const canAdjust = onAdjust !== null && adjusting === null;
  // Side by side, the pair's shape caps its width, so it fits the screen's height.
  const pairAspect = reference.aspect && take.aspect ? reference.aspect + take.aspect : undefined;
  return (
    <div className={`player ${layout}`}>
      <div className={`compare ${layout}`} style={{ "--pair-aspect": pairAspect }}>
        <VideoCell
          aspect={reference.aspect}
          hidden={layout === "take"}
          crop={reference.crop}
          onCropChange={(crop) => changeCrop(referenceFraming, crop)}
          adjustLabel="Adjust the song's video"
          onAdjust={canAdjust && referenceSize ? () => adjust("reference") : null}
        >
          <video
            ref={referenceRef}
            className="frame-video"
            src={referenceUrl}
            playsInline
            preload="auto"
            style={reference.videoStyle}
            onLoadedMetadata={referenceLoaded}
            onTimeUpdate={linked.onTimeUpdate}
          />
        </VideoCell>
        <VideoCell
          aspect={take.aspect}
          crop={take.crop}
          onCropChange={(crop) => changeCrop(takeFraming, crop)}
          adjustLabel="Adjust your take"
          onAdjust={canAdjust && takeAdjustable ? () => adjust("take") : null}
        >
          <video
            ref={takeRef}
            className="frame-video"
            src={takeUrl}
            playsInline
            preload="auto"
            style={take.videoStyle}
            onLoadedMetadata={takeLoaded}
            onTimeUpdate={linked.onTimeUpdate}
            onEnded={linked.pause}
            onError={onTakeUnplayable}
          />
        </VideoCell>
      </div>
      <PlayBar
        playing={linked.playing}
        currentSec={linked.currentSec}
        durationSec={outputTimeFor(takeEndSec ?? takeMediaSec, takeRate, takeStartSec)}
        onToggle={linked.playing ? linked.pause : linked.play}
        onSeek={linked.seek}
      />
      {adjusting && (
        <AdjustPanel
          target={adjusting.target}
          edit={adjusting.edit}
          clipSec={clipTimeFor(linked.currentSec, takeRate, takeStartSec)}
          durationSec={takeMediaSec}
          saving={adjusting.saving}
          onChange={adjusting.onChange}
          onCancel={adjusting.onCancel}
          onDone={adjusting.onDone}
        />
      )}
      <div className="controls">
        <SoundToggle sound={sound} withBoth={tuning} onChange={onSoundChange} />
        <Segmented label="Speed" options={SPEED_OPTIONS} value={speed} onChange={setSpeed} />
        {referenceSize && <LayoutToggle layout={layout} onChange={onLayoutChange} />}
      </div>
    </div>
  );
}

// How to show one video: framed as saved, or, while it's being adjusted, the
// whole picture (turned and mirrored) with the crop drawn over it. Nothing
// until its size is known.
function framed(framing, size, adjusting) {
  if (size === null) return { aspect: null, videoStyle: undefined, crop: null };
  const shown = adjusting ? { ...framing, crop: null } : framing;
  const style = framingStyle(shown, size.width, size.height);
  const crop = adjusting ? mirroredCrop(framing.crop ?? FULL_FRAME, framing.mirror) : null;
  return { aspect: style.aspect, videoStyle: style.video, crop };
}
