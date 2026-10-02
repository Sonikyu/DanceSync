import { useState } from "react";
import {
  clearManualAlignment,
  clipMediaUrl,
  referenceMediaUrl,
  renderSynced,
  setManualAlignment,
  syncedVideoUrl,
} from "../api.js";
import { effectiveAlignment, layoutFor, renderParams, takeRateFor } from "../flow.js";
import { alignmentSummary } from "../tuning.js";
import ComparePlayer from "./ComparePlayer.jsx";
import DownloadButton from "./DownloadButton.jsx";
import FineTune from "./FineTune.jsx";
import useWideViewport from "./useWideViewport.js";
import Working from "./Working.jsx";

// `layoutPick` lives in App, so a picked layout carries over to the next take.
// `startTuning` opens the fine-tune panel straight away, after placing a take
// by hand.
export default function WatchStep({
  song,
  clip,
  onClipChange,
  onChangeMatch,
  onNewTake,
  layoutPick,
  onLayoutPick,
  startTuning,
}) {
  const [status, setStatus] = useState("ready");   // "ready" | "rendering" | "failed"
  const [sound, setSound] = useState("song");
  const [hasReferenceVideo, setHasReferenceVideo] = useState(false);
  // The picture and the room sound come from the take as it was uploaded,
  // played at the alignment's rate, so Watch is ready the moment alignment
  // is. A browser that can't decode it (HEVC outside Safari, .mkv, .avi)
  // gets a render instead: the same take under its room sound, already at
  // full tempo. Either way the song plays live from the song file, and a
  // tuned alignment re-times the take live (takeRate). Only Download, and
  // that fallback, render anything.
  const [takeMedia, setTakeMedia] = useState({ url: clipMediaUrl(clip.id), renderedRate: 1, isRender: false });
  // The alignment being tuned in the fine-tune panel, or null when it's shut.
  const [draft, setDraft] = useState(startTuning ? effectiveAlignment(clip) : null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const wideViewport = useWideViewport();
  const layout = layoutFor({ picked: layoutPick, wideViewport, hasReferenceVideo });
  const alignment = draft ?? effectiveAlignment(clip);
  const takeRate = takeRateFor(alignment.rate, takeMedia.renderedRate);
  const downloadUrl = syncedVideoUrl(clip.id, renderParams(clip, sound, layout));

  // The raw take didn't play here, so play a render of it instead.
  function playRenderInstead() {
    if (takeMedia.isRender) {
      setError("Couldn't play that video. Try again, or try another take.");
      setStatus("failed");
      return;
    }
    const params = renderParams(clip, "room", "take");
    const url = syncedVideoUrl(clip.id, params);
    setStatus("rendering");
    renderSynced(url)
      .then(() => {
        setTakeMedia({ url, renderedRate: params.rate, isRender: true });
        setStatus("ready");
      })
      .catch((err) => {
        setError(err.message);
        setStatus("failed");
      });
  }

  // Both sounds together only exist for tuning by ear.
  function stopTuning() {
    setDraft(null);
    if (sound === "both") setSound("song");
  }

  async function saveTuning(save) {
    setSaving(true);
    setError(null);
    try {
      onClipChange(await save());
      stopTuning();
    } catch (err) {
      setError(err.message);
    }
    setSaving(false);
  }

  return (
    <section className="step">
      <button className="back" onClick={onNewTake}>← New take</button>
      <h1>Your synced video</h1>
      {status === "rendering" && (
        <Working
          label="Preparing your video…"
          progress={null}
          hint="This browser can't play the original file, so it's being converted. About as long as the clip itself."
        />
      )}
      {status === "ready" && (
        <ComparePlayer
          referenceUrl={referenceMediaUrl(song.id)}
          takeUrl={takeMedia.url}
          offsetSec={alignment.offset_sec}
          takeRate={takeRate}
          sound={sound}
          tuning={draft !== null}
          onSoundChange={setSound}
          onReferenceVideo={setHasReferenceVideo}
          onTakeUnplayable={playRenderInstead}
          layout={layout}
          onLayoutChange={onLayoutPick}
        />
      )}
      {error && <p className="error">{error}</p>}
      {draft !== null && status === "ready" && (
        <FineTune
          alignment={draft}
          saving={saving}
          onChange={setDraft}
          onReset={() => saveTuning(() => clearManualAlignment(clip.id))}
          onCancel={stopTuning}
          onDone={() => saveTuning(() => setManualAlignment(clip.id, draft))}
        />
      )}
      {draft === null && (
        <p className="caption">
          {alignmentSummary(clip)} · <button className="link" onClick={onChangeMatch}>Change match</button> ·{" "}
          <button className="link" onClick={() => setDraft(effectiveAlignment(clip))}>Fine-tune</button>
        </p>
      )}
      {status === "ready" && draft === null && (
        <div className="actions">
          <DownloadButton primary url={downloadUrl} label="Download" onError={setError} />
        </div>
      )}
    </section>
  );
}
