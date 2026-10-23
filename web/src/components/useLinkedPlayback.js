import { useEffect, useState } from "react";
import { clipTimeFor, leaderAt, outputTimeFor, playbackRates, referenceTimeFor } from "../flow.js";

// Beyond this much drift the follower jumps straight to the right moment.
// Below it, the follower runs up to MAX_NUDGE faster or slower than its base
// speed to catch up: seeking on every small drift would stall it on keyframe
// decodes and stutter.
const SEEK_DRIFT_SEC = 0.5;
const MAX_NUDGE = 0.1;

// Plays the take and the song media as one, on one clock: output time T, the
// song-relative time the play bar shows (flow.js states the timing model).
// Two media elements never stay locked together on their own, so one leads
// and the other is steered to follow it. The leader is the one making the
// sound (flow.leaderAt): nudging a muted video is invisible, nudging audio
// warbles. `sound` also decides which element is unmuted, so switching it
// is instant.
//
// `timing` is { offsetSec, takeRate, takeStartSec, takeEndSec, speed, sound }:
// where output time 0 is in the song (flow.trimmedOffset), the take media's
// speed relative to the song (flow.takeRateFor), the stretch of the take
// media that plays (a trim; takeEndSec null plays to its end), the review
// speed, and "song", "room" or "both". A change to the offset, rate or trim
// moves the song at once, so tuning is heard and seen straight away.
export default function useLinkedPlayback(takeRef, referenceRef, timing) {
  const { offsetSec, takeRate, takeStartSec, takeEndSec, speed, sound } = timing;
  const [playing, setPlaying] = useState(false);
  const [currentSec, setCurrentSec] = useState(0);
  const rates = playbackRates({ rate: takeRate, speed });

  // defaultPlaybackRate survives a source (re)load, which resets
  // playbackRate to it.
  useEffect(() => {
    for (const [element, rate] of [[takeRef.current, rates.take], [referenceRef.current, rates.reference]]) {
      element.defaultPlaybackRate = rate;
      element.playbackRate = rate;
    }
  }, [takeRef, referenceRef, rates.take, rates.reference]);

  useEffect(() => {
    takeRef.current.muted = sound === "song";
    referenceRef.current.muted = sound === "room";
  }, [takeRef, referenceRef, sound]);

  // Tuning moves the song now rather than drifting it over a second.
  useEffect(() => {
    if (takeRef.current.readyState > 0) realign();
  }, [offsetSec, takeRate, takeStartSec, takeEndSec]);

  // The take's position always converts to T; the song's only while it
  // plays. So the take decides who leads, and the leader decides T.
  function clock() {
    const take = takeRef.current;
    const reference = referenceRef.current;
    const takeOutputSec = outputTimeFor(take.currentTime, takeRate, takeStartSec);
    const leader = leaderAt({ sound, outputSec: takeOutputSec, offsetSec, songDurationSec: reference.duration });
    const outputSec = leader === "take" ? takeOutputSec : reference.currentTime - offsetSec;
    return { leader, outputSec };
  }

  // Wired to both elements' `timeupdate`, which fires about four times a
  // second while playing -- often enough to steer, and unlike
  // requestAnimationFrame it keeps firing in a background tab. Only the
  // leader's updates count, except that a paused song can't lead: when its
  // turn comes at the end of a lead-in, the take's update starts it. Either
  // one stops both at a trimmed end, up to a quarter second late.
  function onTimeUpdate(event) {
    if (playing && pastEnd(takeRef.current)) {
      pause();
      seek(outputTimeFor(takeEndSec, takeRate, takeStartSec));
      return;
    }
    const { leader, outputSec } = clock();
    const reference = referenceRef.current;
    if (playing && leader === "reference" && reference.paused && !reference.ended) {
      const takeOutputSec = outputTimeFor(takeRef.current.currentTime, takeRate, takeStartSec);
      steerReference(reference, takeOutputSec, offsetSec, rates.reference);
      return;
    }
    if (event.target !== elementOf(leader)) return;
    setCurrentSec(outputSec);
    if (!playing) return;
    // The leader runs at exactly its base speed, even if it was nudged while
    // it followed: leadership changes as the song starts or the sound does.
    if (leader === "take") {
      takeRef.current.playbackRate = rates.take;
      steerReference(referenceRef.current, outputSec, offsetSec, rates.reference);
    } else {
      referenceRef.current.playbackRate = rates.reference;
      steer(takeRef.current, clipTimeFor(outputSec, takeRate, takeStartSec), rates.take);
    }
  }

  // Both elements start inside the click, so iOS lets either one make sound
  // later -- even the song during a lead-in, paused again at once until the
  // steering starts it.
  function play() {
    const take = takeRef.current;
    const reference = referenceRef.current;
    if (take.ended || pastEnd(take)) take.currentTime = takeStartSec;   // again from the top, like a native player
    const outputSec = outputTimeFor(take.currentTime, takeRate, takeStartSec);
    jumpReference(reference, outputSec, offsetSec);
    take.play();
    reference.play();
    if (referenceTimeFor(outputSec, offsetSec) === null) reference.pause();
    setPlaying(true);
  }

  function pause() {
    takeRef.current.pause();
    referenceRef.current.pause();
    setPlaying(false);
  }

  function seek(outputSec) {
    takeRef.current.currentTime = clipTimeFor(outputSec, takeRate, takeStartSec);
    jumpReference(referenceRef.current, outputSec, offsetSec);
    setCurrentSec(outputSec);
  }

  // Puts the song at the take's moment, playing or not -- so a paused player
  // shows the matched frame, and a tuned offset or rate applies at once. The
  // take is the reference point because its position always means something;
  // the song's doesn't before it starts. A take outside its trim goes to the
  // trim's start first.
  function realign() {
    const take = takeRef.current;
    const outsideTrim = take.currentTime < takeStartSec || (takeEndSec !== null && take.currentTime > takeEndSec);
    if (outsideTrim) take.currentTime = takeStartSec;
    const outputSec = outputTimeFor(take.currentTime, takeRate, takeStartSec);
    jumpReference(referenceRef.current, outputSec, offsetSec);
    setCurrentSec(outputSec);
  }

  function pastEnd(take) {
    return takeEndSec !== null && take.currentTime >= takeEndSec;
  }

  function elementOf(leader) {
    return leader === "take" ? takeRef.current : referenceRef.current;
  }

  return { playing, currentSec, play, pause, seek, realign, onTimeUpdate };
}

function steerReference(reference, outputSec, offsetSec, baseRate) {
  const targetSec = referenceTimeFor(outputSec, offsetSec);
  if (targetSec === null) {
    reference.pause();   // the song hasn't started yet; hold its first frame
    return;
  }
  steer(reference, targetSec, baseRate);
  if (reference.paused && !reference.ended) reference.play();
}

function steer(follower, targetSec, baseRate) {
  const driftSec = targetSec - follower.currentTime;
  if (Math.abs(driftSec) > SEEK_DRIFT_SEC) follower.currentTime = targetSec;
  follower.playbackRate = baseRate + Math.min(Math.max(driftSec, -MAX_NUDGE), MAX_NUDGE);
}

function jumpReference(reference, outputSec, offsetSec) {
  reference.currentTime = referenceTimeFor(outputSec, offsetSec) ?? 0;
}
