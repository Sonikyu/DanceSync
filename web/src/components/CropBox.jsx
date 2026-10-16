import { useRef } from "react";
import { dragCrop } from "../editing.js";

const CORNERS = ["nw", "ne", "sw", "se"];

// A crop box over a video, dragged by its body to move it and by its
// corners to resize it. Pointer events, so a finger works like a mouse; the
// layer takes every touch, so dragging never scrolls the page. `crop` is in
// the coordinates of the picture as shown (editing.mirroredCrop converts a
// mirrored one), and every move goes to `onChange` in the same coordinates.
export default function CropBox({ crop, onChange }) {
  const layerRef = useRef(null);
  const dragRef = useRef(null);   // { handle, x, y, crop } where the drag started

  function startDrag(event, handle) {
    event.stopPropagation();   // a corner isn't also the body
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = { handle, x: event.clientX, y: event.clientY, crop };
  }

  // Captured pointer events still bubble here from the box or corner.
  function drag(event) {
    const start = dragRef.current;
    if (start === null) return;
    const layer = layerRef.current.getBoundingClientRect();
    const dx = (event.clientX - start.x) / layer.width;
    const dy = (event.clientY - start.y) / layer.height;
    onChange(dragCrop(start.crop, start.handle, dx, dy));
  }

  function endDrag() {
    dragRef.current = null;
  }

  const box = { left: `${crop.x * 100}%`, top: `${crop.y * 100}%`, width: `${crop.w * 100}%`, height: `${crop.h * 100}%` };
  return (
    <div className="crop-layer" ref={layerRef} onPointerMove={drag} onPointerUp={endDrag} onPointerCancel={endDrag}>
      <div className="crop-box" style={box} onPointerDown={(event) => startDrag(event, "move")}>
        {CORNERS.map((corner) => (
          <span key={corner} className={`crop-handle ${corner}`} onPointerDown={(event) => startDrag(event, corner)} />
        ))}
      </div>
    </div>
  );
}
