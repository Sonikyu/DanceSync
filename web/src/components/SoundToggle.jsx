import Segmented from "./Segmented.jsx";

// "Song" is the clean original track. "Room" is the phone's own recording of
// the practice -- the speaker, counts, footsteps -- sped up to full speed.
// "Both", offered while tuning, plays them together: in sync they blend into
// one sound, and out of sync they echo. Downloads only have Song and Room.
const OPTIONS = [
  { value: "song", label: "Song" },
  { value: "room", label: "Room" },
];
const BOTH = { value: "both", label: "Both" };

export default function SoundToggle({ sound, withBoth, onChange }) {
  const options = withBoth ? [...OPTIONS, BOTH] : OPTIONS;
  return <Segmented label="Sound" options={options} value={sound} onChange={onChange} />;
}
