import { useEffect, useRef, useState } from "react";

// How much of the song each candidate preview plays.
const PREVIEW_SEC = 8;

// Plays a few seconds of the song from a candidate's offset, one candidate at
// a time. Starting another candidate cuts off the first; toggling the one
// that's playing stops it.
export default function useSongPreview(src) {
  const audioRef = useRef(null);
  const [playingIndex, setPlayingIndex] = useState(null);

  useEffect(() => {
    const audio = new Audio(src);
    audio.preload = "metadata";
    audioRef.current = audio;
    return () => audio.pause();
  }, [src]);

  function stop() {
    audioRef.current.pause();
    setPlayingIndex(null);
  }

  function toggle(index, offsetSec) {
    if (index === playingIndex) {
      stop();
      return;
    }
    const audio = audioRef.current;
    const startSec = Math.max(offsetSec, 0);
    audio.currentTime = startSec;
    audio.ontimeupdate = () => audio.currentTime >= startSec + PREVIEW_SEC && stop();
    audio.onended = stop;
    audio.play().catch(stop);
    setPlayingIndex(index);
  }

  return { playingIndex, toggle, stop };
}
