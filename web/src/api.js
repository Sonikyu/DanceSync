// Fetch wrappers for the FastAPI backend. Paths are relative: in dev, Vite
// proxies /api to the server, so the browser only ever talks to one origin.

const UNREACHABLE = "Can't reach the DanceSync server. Is it running?";

// The server's error text is written for developers; these are for dancers.
const MESSAGES = {
  401: "You've been signed out. Reload the page to sign in again.",
  413: "That file's too big. Songs can be up to 100 MB and videos up to 500 MB.",
  415: "That file type isn't supported. Use a video (.mp4, .mov) or audio file (.mp3, .m4a, .wav).",
};

// `{ signed_in }`. Always true when the server has no passphrase set.
export function getSession() {
  return request("/api/session");
}

// Resolves on success. The session cookie it sets covers every later
// request, including the range requests <video> and <audio> make.
export async function signIn(passphrase) {
  const resp = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ passphrase }),
  }).catch(() => {
    throw new Error(UNREACHABLE);
  });
  if (resp.status === 401) throw new Error("That's not the passphrase. Try again.");
  if (!resp.ok) throw new Error("Something went wrong on the server. Try again.");
}

export function listReferences() {
  return request("/api/references");
}

export function uploadReference(file, onProgress) {
  return upload("/api/references", file, onProgress);
}

export function uploadClip(referenceId, file, onProgress) {
  const query = new URLSearchParams({ reference_id: referenceId });
  return upload(`/api/clips?${query}`, file, onProgress);
}

export function selectCandidate(clipId, index) {
  return request(`/api/clips/${clipId}/select`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ index }),
  });
}

// The song file itself: audio for previews, video for the side-by-side view.
export function referenceMediaUrl(referenceId) {
  return `/api/references/${referenceId}/media`;
}

// `sound` is "song" or "room"; `layout` is "take" or "side-by-side". The
// server renders whichever candidate is selected -- `candidate` in the query
// only stops the browser replaying a cached render of a different one.
export function syncedVideoUrl(clipId, candidateIndex, sound, layout) {
  const query = new URLSearchParams({ candidate: candidateIndex, sound, layout });
  return `/api/clips/${clipId}/synced?${query}`;
}

// HEAD makes the server render (if it hasn't already) without sending the
// video, so the UI can wait for the render before handing the URL to <video>.
export async function renderSynced(url) {
  const resp = await fetch(url, { method: "HEAD" }).catch(() => {
    throw new Error(UNREACHABLE);
  });
  if (!resp.ok) throw new Error("Couldn't make that video. Try again, or try another take.");
}

async function request(url, options) {
  const resp = await fetch(url, options).catch(() => {
    throw new Error(UNREACHABLE);
  });
  return parseResponse(resp.status, await resp.text());
}

// XMLHttpRequest rather than fetch: fetch can't report upload progress, and a
// practice video can be hundreds of megabytes. `onProgress` gets 0 to 1.
function upload(url, file, onProgress) {
  const form = new FormData();
  form.append("file", file);
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.upload.onprogress = (event) => onProgress(event.loaded / event.total);
    xhr.onload = () => resolve(xhr);
    xhr.onerror = () => reject(new Error(UNREACHABLE));
    xhr.send(form);
  }).then((xhr) => parseResponse(xhr.status, xhr.responseText));
}

function parseResponse(status, text) {
  if (status < 400) return JSON.parse(text);
  throw new Error(MESSAGES[status] ?? "Something went wrong on the server. Try again.");
}
