import { songTitle } from "../flow.js";

// Shown instead of the player when the matcher found nothing convincing.
// "Watch anyway" stays available: the threshold can be wrong on a very
// noisy take, and watching the best guess costs nothing.
export default function NoMatchStep({ song, onNewTake, onNewSong, onWatchAnyway }) {
  return (
    <section className="step">
      <button className="back" onClick={onNewTake}>← New take</button>
      <h1>We couldn't find this take in the song</h1>
      <p className="lede">The video's sound doesn't line up with {songTitle(song.filename)} anywhere.</p>
      <ul className="reasons">
        <li><strong>A different song?</strong> Check you picked the track you danced to.</li>
        <li><strong>An unusual speed?</strong> Takes at full, ¾ or ½ speed work best.</li>
        <li><strong>Too quiet?</strong> The phone needs to hear the music over the room. Turn the speaker up, or film closer to it.</li>
      </ul>
      <div className="actions">
        <button className="button" onClick={onNewSong}>Change song</button>
        <button className="button primary" onClick={onNewTake}>New video</button>
      </div>
      <p className="caption">
        <button className="link" onClick={onWatchAnyway}>Watch the best guess anyway</button>
      </p>
    </section>
  );
}
