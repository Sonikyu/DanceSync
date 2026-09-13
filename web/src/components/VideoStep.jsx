import { useState } from "react";
import { uploadClip } from "../api.js";
import { songTitle } from "../flow.js";
import DropZone from "./DropZone.jsx";
import Working from "./Working.jsx";

export default function VideoStep({ song, onBack, onAligned }) {
  const [progress, setProgress] = useState(null);   // null = not uploading
  const [error, setError] = useState(null);

  async function addVideo(file) {
    setError(null);
    setProgress(0);
    try {
      onAligned(await uploadClip(song.id, file, setProgress));
    } catch (err) {
      setError(err.message);
      setProgress(null);
    }
  }

  if (progress !== null) {
    const uploaded = progress >= 1;
    return (
      <section className="step">
        <Working
          label={uploaded ? "Finding your place in the song…" : "Uploading your video"}
          progress={uploaded ? null : progress}
          hint={uploaded ? "This takes 10 to 30 seconds." : null}
        />
      </section>
    );
  }

  return (
    <section className="step">
      <button className="back" onClick={onBack}>← Back</button>
      <h1>Add your practice video</h1>
      <p className="lede">Dancing to {songTitle(song.filename)}. Any practice speed works.</p>
      <DropZone large accept="video/*" label="Choose a video" hint="or drop it here · MOV or MP4, up to 500 MB" onFile={addVideo} />
      {error && <p className="error">{error}</p>}
    </section>
  );
}
