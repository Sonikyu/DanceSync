import { useEffect, useState } from "react";
import { referenceMediaUrl, renderSynced, syncedVideoUrl } from "../api.js";
import { chosenCandidate, formatRate, formatTime, layoutFor, renderParams } from "../flow.js";
import ComparePlayer from "./ComparePlayer.jsx";
import DownloadButton from "./DownloadButton.jsx";
import useWideViewport from "./useWideViewport.js";
import Working from "./Working.jsx";

// `layoutPick` lives in App, so a picked layout carries over to the next take.
export default function WatchStep({ song, clip, onChangeMatch, onNewTake, layoutPick, onLayoutPick }) {
  const [status, setStatus] = useState("rendering");   // "rendering" | "ready" | "failed"
  const [sound, setSound] = useState("song");
  const [roomAvailable, setRoomAvailable] = useState(false);
  const [hasReferenceVideo, setHasReferenceVideo] = useState(false);
  const [error, setError] = useState(null);
  const wideViewport = useWideViewport();
  const layout = layoutFor({ picked: layoutPick, wideViewport, hasReferenceVideo });
  const candidate = chosenCandidate(clip);
  const videoUrl = (sound, layout) => syncedVideoUrl(clip.id, renderParams(clip, sound, layout));
  const songTakeUrl = videoUrl("song", "take");
  const roomTakeUrl = videoUrl("room", "take");

  // Both sounds render up front, so switching between them is instant. Only
  // the song is required: if the room render fails, Room just stays off.
  useEffect(() => {
    renderSynced(roomTakeUrl)
      .then(() => setRoomAvailable(true))
      .catch(() => setRoomAvailable(false));
    renderSynced(songTakeUrl)
      .then(() => setStatus("ready"))
      .catch((err) => {
        setError(err.message);
        setStatus("failed");
      });
  }, [songTakeUrl, roomTakeUrl]);

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
          takeUrl={videoUrl(sound, "take")}
          offsetSec={candidate.offset_sec}
          sound={sound}
          roomAvailable={roomAvailable}
          onSoundChange={setSound}
          onReferenceVideo={setHasReferenceVideo}
          layout={layout}
          onLayoutChange={onLayoutPick}
        />
      )}
      {error && <p className="error">{error}</p>}
      <p className="caption">
        Matched at {formatTime(candidate.offset_sec)} · {formatRate(candidate.rate)} ·{" "}
        <button className="link" onClick={onChangeMatch}>Change match</button>
      </p>
      {status === "ready" && (
        <div className="actions">
          <DownloadButton primary url={videoUrl(sound, layout)} label="Download" onError={setError} />
        </div>
      )}
    </section>
  );
}
