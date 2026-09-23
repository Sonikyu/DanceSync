import Segmented from "./Segmented.jsx";

// The reference beside the take, above it, or the take alone. Download saves
// whichever is showing.
const OPTIONS = [
  { value: "side-by-side", label: "Side by side" },
  { value: "stacked", label: "Stacked" },
  { value: "take", label: "Take only" },
];

export default function LayoutToggle({ layout, onChange }) {
  return <Segmented label="Layout" options={OPTIONS} value={layout} onChange={onChange} />;
}
