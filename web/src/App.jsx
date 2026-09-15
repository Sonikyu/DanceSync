import { useState } from "react";
import { stageOf, stepAfterAlignment } from "./flow.js";
import MatchStep from "./components/MatchStep.jsx";
import SongStep from "./components/SongStep.jsx";
import StepDots from "./components/StepDots.jsx";
import VideoStep from "./components/VideoStep.jsx";
import WatchStep from "./components/WatchStep.jsx";

// One screen at a time: song -> video -> match (only when ambiguous) -> watch.
export default function App() {
  const [step, setStep] = useState("song");
  const [song, setSong] = useState(null);
  const [clip, setClip] = useState(null);

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
      {step === "song" && <SongStep onPick={pickSong} />}
      {step === "video" && (
        <VideoStep song={song} onBack={() => setStep("song")} onAligned={finishAlignment} />
      )}
      {step === "match" && (
        <MatchStep song={song} clip={clip} onBack={() => setStep("video")} onPicked={finishMatch} />
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
