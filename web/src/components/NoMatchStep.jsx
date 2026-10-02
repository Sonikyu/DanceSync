import { songTitle } from "../flow.js";

// Shown instead of the player when the matcher found nothing convincing. The
// way forward is placing the take by hand. "Watch anyway" stays too: the
// threshold can be wrong on a very noisy take, and the best guess is free.
export default function NoMatchStep({ song, onNewTake, onNewSong, onPlaceByHand, onWatchAnyway }) {
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
      <div className="actions stacked-actions">
        <button className="button primary" onClick={onPlaceByHand}>Place it by hand</button>
        <div className="actions-row">
          <button className="button" onClick={onNewSong}>Change song</button>
          <button className="button" onClick={onNewTake}>New video</button>
        </div>
      </div>
      <p className="caption">
        <button className="link" onClick={onWatchAnyway}>Watch the best guess anyway</button>
      </p>
    </section>
  );
}
