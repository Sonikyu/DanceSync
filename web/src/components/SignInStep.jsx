import { useState } from "react";
import { signIn } from "../api.js";

export default function SignInStep({ onSignedIn }) {
  const [passphrase, setPassphrase] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function submit(event) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await signIn(passphrase);
      onSignedIn();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <form className="step" onSubmit={submit}>
      <h1>Sign in</h1>
      <p className="lede">Enter the passphrase you were given.</p>
      <input
        className="field"
        type="password"
        autoComplete="current-password"
        aria-label="Passphrase"
        value={passphrase}
        onChange={(event) => setPassphrase(event.target.value)}
        autoFocus
      />
      <button className="button primary" type="submit" disabled={busy || !passphrase}>
        {busy ? "Signing in…" : "Sign in"}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
