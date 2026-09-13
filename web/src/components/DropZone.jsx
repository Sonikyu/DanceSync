import { useState } from "react";

// A file picker that also takes drag-and-drop. The real <input> stays in the
// page, visually hidden, so it's still reachable by keyboard.
export default function DropZone({ accept, label, hint, large, onFile }) {
  const [dragging, setDragging] = useState(false);

  function dragOver(event) {
    event.preventDefault();
    setDragging(true);
  }

  function drop(event) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) onFile(file);
  }

  function choose(event) {
    const file = event.target.files[0];
    event.target.value = "";   // so choosing the same file again still fires
    if (file) onFile(file);
  }

  const className = ["dropzone", large && "large", dragging && "dragging"].filter(Boolean).join(" ");
  return (
    <label className={className} onDragOver={dragOver} onDragLeave={() => setDragging(false)} onDrop={drop}>
      <input className="sr-only" type="file" accept={accept} onChange={choose} />
      <span className="dropzone-label">{label}</span>
      <span className="hint">{hint}</span>
    </label>
  );
}
