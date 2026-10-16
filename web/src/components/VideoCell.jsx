import CropBox from "./CropBox.jsx";

// One video on Watch: its frame, which shows only the crop (`aspect` is the
// crop's shape; the video inside is placed by editing.framingStyle), the
// crop box over it while it's being adjusted (`crop` set), and an Adjust
// button under it (`onAdjust` set).
export default function VideoCell({ aspect, hidden, crop, onCropChange, adjustLabel, onAdjust, children }) {
  return (
    <div className="compare-cell" hidden={hidden} style={{ "--aspect": aspect }}>
      <div className="frame">
        {children}
        {crop && <CropBox crop={crop} onChange={onCropChange} />}
      </div>
      {onAdjust && (
        <button className="link adjust-link" aria-label={adjustLabel} onClick={onAdjust}>
          Adjust
        </button>
      )}
    </div>
  );
}
