import Segmented from "./Segmented.jsx";

// "Song" is the clean original track. "Room" is the phone's own recording of
// the practice -- the speaker, counts, footsteps -- sped up to full speed.
const OPTIONS = [
  { value: "song", label: "Song" },
  { value: "room", label: "Room" },
];

export default function SoundToggle({ sound, onChange }) {
  return <Segmented label="Sound" options={OPTIONS} value={sound} onChange={onChange} />;
}
