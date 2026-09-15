import { useState } from "react";
import { renderSynced } from "../api.js";
import { DownloadIcon } from "./icons.jsx";

// Asks the server to render first, then starts the download -- so the button
// can say "Preparing…" rather than the browser sitting silent for seconds.
export default function DownloadButton({ url, label, primary, onError }) {
  const [preparing, setPreparing] = useState(false);

  async function download() {
    if (preparing) return;
    setPreparing(true);
    try {
      await renderSynced(url);
      saveFile(url);
    } catch (err) {
      onError(err.message);
    }
    setPreparing(false);
  }

  return (
    <button className={primary ? "button primary" : "button"} onClick={download}>
      <DownloadIcon />
      {preparing ? "Preparing…" : label}
    </button>
  );
}

function saveFile(url) {
  const link = document.createElement("a");
  link.href = url;
  link.download = "";
  link.click();
}
