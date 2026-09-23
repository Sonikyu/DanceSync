import { useEffect, useState } from "react";
import { getSession } from "./api.js";
import { stageOf, stepAfterAlignment } from "./flow.js";
import MatchStep from "./components/MatchStep.jsx";
import NoMatchStep from "./components/NoMatchStep.jsx";
import SignInStep from "./components/SignInStep.jsx";
import SongStep from "./components/SongStep.jsx";
import StepDots from "./components/StepDots.jsx";
import VideoStep from "./components/VideoStep.jsx";
import WatchStep from "./components/WatchStep.jsx";

// One screen at a time: song -> video -> match (only when ambiguous) -> watch.
// A failed match shows "no match" in place of watch.
// Sign-in comes first, only when the server has a passphrase set.
export default function App() {
  const [signedIn, setSignedIn] = useState(null);   // null = still asking the server
  const [step, setStep] = useState("song");
  const [song, setSong] = useState(null);
  const [clip, setClip] = useState(null);

  useEffect(() => {
    // Unreachable server: carry on, so the song step shows its own error.
    getSession().then((session) => setSignedIn(session.signed_in)).catch(() => setSignedIn(true));
  }, []);

  function pickSong(reference) {
    setSong(reference);
    setStep("video");
  }

  function finishAlignment(alignedClip) {
    setClip(alignedClip);
    setStep(stepAfterAlignment(alignedClip));
  }

  function finishMatch(updatedClip) {
    setClip(updatedClip);
    setStep("watch");
  }

  return (
    <div className="app">
      <header className="header">
        <span className="wordmark">DanceSync</span>
        <StepDots current={stageOf(step)} />
      </header>
      {signedIn === false && <SignInStep onSignedIn={() => setSignedIn(true)} />}
      {signedIn && step === "song" && <SongStep onPick={pickSong} />}
      {step === "video" && (
        <VideoStep song={song} onBack={() => setStep("song")} onAligned={finishAlignment} />
      )}
      {step === "match" && (
        <MatchStep song={song} clip={clip} onBack={() => setStep("video")} onPicked={finishMatch} />
      )}
      {step === "nomatch" && (
        <NoMatchStep
          song={song}
          onNewTake={() => setStep("video")}
          onNewSong={() => setStep("song")}
          onWatchAnyway={() => setStep("watch")}
        />
      )}
      {step === "watch" && (
        <WatchStep
          song={song}
          clip={clip}
          onChangeMatch={() => setStep("match")}
          onNewTake={() => setStep("video")}
        />
      )}
    </div>
  );
}
