// "Song" is the clean original track. "Room" is the phone's own recording of
// the practice -- the speaker, counts, footsteps -- sped up to full speed.
const OPTIONS = [
  { value: "song", label: "Song" },
  { value: "room", label: "Room" },
];

export default function SoundToggle({ sound, roomAvailable, onChange }) {
  return (
    <div className="sound">
      <span className="hint" id="sound-label">Sound</span>
      <div className="segmented" role="radiogroup" aria-labelledby="sound-label">
        {OPTIONS.map((option) => (
          <button
            key={option.value}
            role="radio"
            aria-checked={sound === option.value}
            disabled={option.value === "room" && !roomAvailable}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
