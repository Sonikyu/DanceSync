import { useState } from "react";
import { referenceMediaUrl, selectCandidate } from "../api.js";
import CandidateCard from "./CandidateCard.jsx";
import SongTimeline from "./SongTimeline.jsx";
import useSongPreview from "./useSongPreview.js";

export default function MatchStep({ song, clip, onBack, onPicked }) {
  const candidates = clip.alignment.top_candidates;
  const preview = useSongPreview(referenceMediaUrl(song.id));
  const [error, setError] = useState(null);

  async function pick(index) {
    preview.stop();
    try {
      onPicked(await selectCandidate(clip.id, index));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="step">
      <button className="back" onClick={onBack}>← Back</button>
      <h1>Which part did you dance?</h1>
      <p className="lede">
        {clip.alignment.ambiguous
          ? "A few parts of this song sound alike. Play each one and pick yours."
          : "These are the closest matches. Play each one and pick yours."}
      </p>
      <SongTimeline durationSec={song.duration_sec} candidates={candidates} playingIndex={preview.playingIndex} />
      <ol className="cards">
        {candidates.map((candidate, index) => (
          <CandidateCard
            key={index}
            candidates={candidates}
            index={index}
            playing={preview.playingIndex === index}
            onPlay={() => preview.toggle(index, candidate.offset_sec)}
            onPick={() => pick(index)}
          />
        ))}
      </ol>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
