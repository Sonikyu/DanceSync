import { useEffect, useState } from "react";
import { referenceMediaUrl, renderSynced, syncedVideoUrl } from "../api.js";
import { effectiveAlignment, formatRate, formatTime, layoutFor, renderParams, takeRateFor } from "../flow.js";
import ComparePlayer from "./ComparePlayer.jsx";
import DownloadButton from "./DownloadButton.jsx";
import useWideViewport from "./useWideViewport.js";
import Working from "./Working.jsx";

// `layoutPick` lives in App, so a picked layout carries over to the next take.
export default function WatchStep({ song, clip, onChangeMatch, onNewTake, layoutPick, onLayoutPick }) {
  const [status, setStatus] = useState("rendering");   // "rendering" | "ready" | "failed"
  const [sound, setSound] = useState("song");
  const [hasReferenceVideo, setHasReferenceVideo] = useState(false);
  // The picture is one render of the take under its room sound, made at the
  // alignment this screen opened with. The song plays live from the song
  // file, and a tuned alignment re-times the render live (takeRate), so
  // tuning never waits on a render. Only Download renders anything else.
  const [previewClip] = useState(clip);
  const [error, setError] = useState(null);
  const wideViewport = useWideViewport();
  const layout = layoutFor({ picked: layoutPick, wideViewport, hasReferenceVideo });
  const alignment = effectiveAlignment(clip);
  const takeRate = takeRateFor(alignment.rate, effectiveAlignment(previewClip).rate);
  const previewUrl = syncedVideoUrl(clip.id, renderParams(previewClip, "room", "take"));
  const downloadUrl = syncedVideoUrl(clip.id, renderParams(clip, sound, layout));

  useEffect(() => {
    renderSynced(previewUrl)
      .then(() => setStatus("ready"))
      .catch((err) => {
        setError(err.message);
        setStatus("failed");
      });
  }, [previewUrl]);

  return (
    <section className="step">
      <button className="back" onClick={onNewTake}>← New take</button>
      <h1>Your synced video</h1>
      {status === "rendering" && (
        <Working label="Making your synced video…" progress={null} hint="About as long as the clip itself." />
      )}
      {status === "ready" && (
        <ComparePlayer
          referenceUrl={referenceMediaUrl(song.id)}
          takeUrl={previewUrl}
          offsetSec={alignment.offset_sec}
          takeRate={takeRate}
          sound={sound}
          onSoundChange={setSound}
          onReferenceVideo={setHasReferenceVideo}
          layout={layout}
          onLayoutChange={onLayoutPick}
        />
      )}
      {error && <p className="error">{error}</p>}
      <p className="caption">
        Matched at {formatTime(alignment.offset_sec)} · {formatRate(alignment.rate)} ·{" "}
        <button className="link" onClick={onChangeMatch}>Change match</button>
      </p>
      {status === "ready" && (
        <div className="actions">
          <DownloadButton primary url={downloadUrl} label="Download" onError={setError} />
        </div>
      )}
    </section>
  );
}
