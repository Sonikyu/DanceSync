import Segmented from "./Segmented.jsx";

// "Song" is the clean original track. "Room" is the phone's own recording of
// the practice -- the speaker, counts, footsteps -- sped up to full speed.
export default function SoundToggle({ sound, roomAvailable, onChange }) {
  const options = [
    { value: "song", label: "Song" },
    { value: "room", label: "Room", disabled: !roomAvailable },
  ];
  return <Segmented label="Sound" options={options} value={sound} onChange={onChange} />;
}
