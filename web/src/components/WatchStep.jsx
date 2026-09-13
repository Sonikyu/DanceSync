import { useEffect, useState } from "react";
import { referenceMediaUrl, renderSynced, syncedVideoUrl } from "../api.js";
import { chosenCandidate, chosenIndex, formatRate, formatTime } from "../flow.js";
import ComparePlayer from "./ComparePlayer.jsx";
import DownloadButton from "./DownloadButton.jsx";
import Working from "./Working.jsx";

export default function WatchStep({ song, clip, onChangeMatch, onNewTake }) {
  const [status, setStatus] = useState("rendering");   // "rendering" | "ready" | "failed"
  const [sound, setSound] = useState("song");
  const [roomAvailable, setRoomAvailable] = useState(false);
  const [hasReferenceVideo, setHasReferenceVideo] = useState(false);
  const [error, setError] = useState(null);
  const index = chosenIndex(clip);
  const candidate = chosenCandidate(clip);

  // Both sounds render up front, so switching between them is instant. Only
  // the song is required: if the room render fails, Room just stays off.
  useEffect(() => {
    renderSynced(syncedVideoUrl(clip.id, index, "room", "take"))
      .then(() => setRoomAvailable(true))
      .catch(() => setRoomAvailable(false));
    renderSynced(syncedVideoUrl(clip.id, index, "song", "take"))
      .then(() => setStatus("ready"))
      .catch((err) => {
        setError(err.message);
        setStatus("failed");
      });
  }, [clip.id, index]);

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
          takeUrl={syncedVideoUrl(clip.id, index, sound, "take")}
          offsetSec={candidate.offset_sec}
          sound={sound}
          roomAvailable={roomAvailable}
          onSoundChange={setSound}
          onReferenceVideo={setHasReferenceVideo}
        />
      )}
      {error && <p className="error">{error}</p>}
      <p className="caption">
        Matched at {formatTime(candidate.offset_sec)} · {formatRate(candidate.rate)} ·{" "}
        <button className="link" onClick={onChangeMatch}>Change match</button>
      </p>
      {status === "ready" && (
        <div className="actions">
          {hasReferenceVideo && (
            <DownloadButton
              url={syncedVideoUrl(clip.id, index, sound, "side-by-side")}
              label="Side by side"
              onError={setError}
            />
          )}
          <DownloadButton
            primary
            url={syncedVideoUrl(clip.id, index, sound, "take")}
            label={hasReferenceVideo ? "Your take" : "Download"}
            onError={setError}
          />
        </div>
      )}
    </section>
  );
}
