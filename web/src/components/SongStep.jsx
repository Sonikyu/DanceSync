import { useEffect, useState } from "react";
import { importReference, listReferences, uploadReference } from "../api.js";
import { formatTime, songTitle } from "../flow.js";
import DropZone from "./DropZone.jsx";
import Working from "./Working.jsx";

export default function SongStep({ onPick }) {
  const [songs, setSongs] = useState([]);
  const [progress, setProgress] = useState(null);   // null = not uploading
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    listReferences().then(setSongs).catch((err) => setError(err.message));
  }, []);

  async function addSong(file) {
    setError(null);
    setProgress(0);
    try {
      onPick(await uploadReference(file, setProgress));
    } catch (err) {
      setError(err.message);
      setProgress(null);
    }
  }

  async function importSong(url) {
    setError(null);
    setImporting(true);
    try {
      onPick(await importReference(url));
    } catch (err) {
      setError(err.message);
      setImporting(false);
    }
  }

  if (importing) {
    return (
      <section className="step">
        <Working label="Downloading from YouTube…" progress={null} hint="This can take a minute." />
      </section>
    );
  }

  if (progress !== null) {
    const uploaded = progress >= 1;
    return (
      <section className="step">
        <Working label={uploaded ? "Reading the song…" : "Uploading your song"} progress={uploaded ? null : progress} />
      </section>
    );
  }

  return (
    <section className="step">
      <h1>Choose your song</h1>
      <p className="lede">The original track, at full speed.</p>
      {songs.length > 0 && <SongList songs={songs} onPick={onPick} />}
      <DropZone
        accept="audio/*,video/*"
        label={songs.length > 0 ? "Add a new song" : "Choose a song file"}
        hint="or drop it here · MP3, M4A, WAV"
        onFile={addSong}
      />
      <LinkForm onSubmit={importSong} />
      {error && <p className="error">{error}</p>}
    </section>
  );
}

function SongList({ songs, onPick }) {
  return (
    <ul className="list">
      {songs.map((song) => (
        <li key={song.id}>
          <button className="list-item" onClick={() => onPick(song)}>
            <span className="name">{songTitle(song.filename)}</span>
            <span className="meta">{formatTime(song.duration_sec)}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function LinkForm({ onSubmit }) {
  const [url, setUrl] = useState("");

  function submit(event) {
    event.preventDefault();
    onSubmit(url.trim());
  }

  return (
    <form className="link-form" onSubmit={submit}>
      <input
        className="field"
        type="url"
        placeholder="or paste a YouTube link"
        aria-label="YouTube link"
        value={url}
        onChange={(event) => setUrl(event.target.value)}
      />
      <button className="button" type="submit" disabled={!url.trim()}>
        Import
      </button>
    </form>
  );
}
