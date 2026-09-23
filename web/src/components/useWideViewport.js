import { useEffect, useState } from "react";
import { WIDE_VIEWPORT_QUERY } from "../flow.js";

// Whether the window is wide enough for side by side by default. Follows
// resizes and phone rotation, as the CSS media query it replaces did.
export default function useWideViewport() {
  const [wide, setWide] = useState(() => window.matchMedia(WIDE_VIEWPORT_QUERY).matches);

  useEffect(() => {
    const query = window.matchMedia(WIDE_VIEWPORT_QUERY);
    const update = () => setWide(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  return wide;
}
