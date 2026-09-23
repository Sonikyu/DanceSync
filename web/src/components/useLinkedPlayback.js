import { useEffect, useState } from "react";
import { referenceTimeFor } from "../flow.js";

// Beyond this much drift the reference jumps straight to the right moment.
// Below it, the reference runs up to MAX_NUDGE faster or slower than its base
// speed to catch up: seeking on every small drift would stall it on keyframe
// decodes and stutter.
const SEEK_DRIFT_SEC = 0.5;
const MAX_NUDGE = 0.1;

// Plays the take and keeps the reference video in step with it. The take is
// the clock -- the shared play bar drives it -- and the reference follows,
// since two <video> elements never stay locked together on their own.
// `rates` (flow.playbackRates) sets each one's base speed for review speed;
// browsers keep the pitch when it isn't 1.
export default function useLinkedPlayback(takeRef, referenceRef, offsetSec, rates) {
  const [playing, setPlaying] = useState(false);
  const [currentSec, setCurrentSec] = useState(0);

  // Mid-playback too: a rate change doesn't move either element, and the
  // reference's nudge rebases on its new speed at the next time update.
  // defaultPlaybackRate survives a source (re)load, which resets
  // playbackRate to it -- as swapping the take for the other sound does.
  useEffect(() => {
    for (const [element, rate] of [[takeRef.current, rates.take], [referenceRef.current, rates.reference]]) {
      element.defaultPlaybackRate = rate;
      element.playbackRate = rate;
    }
  }, [takeRef, referenceRef, rates.take, rates.reference]);

  // Wired to the take's `timeupdate`, which fires about four times a second
  // while it plays -- often enough to steer the reference, and unlike
  // requestAnimationFrame it keeps firing when the tab is in the background.
  function onTimeUpdate() {
    const take = takeRef.current;
    setCurrentSec(take.currentTime);
    if (!take.paused) followTake(take, referenceRef.current, offsetSec, rates.reference);
  }

  function play() {
    const take = takeRef.current;
    if (take.ended) take.currentTime = 0;   // play again from the top, like a native player
    jumpReference(referenceRef.current, take.currentTime, offsetSec);
    take.play();
    setPlaying(true);
  }

  function pause() {
    takeRef.current.pause();
    referenceRef.current.pause();
    setPlaying(false);
  }

  function seek(sec) {
    takeRef.current.currentTime = sec;
    jumpReference(referenceRef.current, sec, offsetSec);
    setCurrentSec(sec);
  }

  // Puts the reference at the take's moment without playing either -- so a
  // paused player shows the matched frame, not the song's first.
  function alignReference() {
    jumpReference(referenceRef.current, takeRef.current.currentTime, offsetSec);
  }

  return { playing, currentSec, play, pause, seek, alignReference, onTimeUpdate };
}

function followTake(take, reference, offsetSec, referenceRate) {
  const targetSec = referenceTimeFor(take.currentTime, offsetSec);
  if (targetSec === null) {
    reference.pause();   // the song hasn't started yet; hold its first frame
    return;
  }
  const driftSec = targetSec - reference.currentTime;
  if (Math.abs(driftSec) > SEEK_DRIFT_SEC) reference.currentTime = targetSec;
  reference.playbackRate = referenceRate + Math.min(Math.max(driftSec, -MAX_NUDGE), MAX_NUDGE);
  if (reference.paused) reference.play();
}

function jumpReference(reference, takeSec, offsetSec) {
  reference.currentTime = referenceTimeFor(takeSec, offsetSec) ?? 0;
}
