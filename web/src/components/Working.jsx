// A labeled progress bar. `progress` is 0 to 1, or null while the server is
// busy and can't say how far along it is.
export default function Working({ label, progress, hint }) {
  const determinate = progress !== null;
  return (
    <div className="working" role="status">
      <p className="working-label">
        <span>{label}</span>
        {determinate && <span>{Math.round(progress * 100)}%</span>}
      </p>
      <div className={determinate ? "progress" : "progress indeterminate"}>
        <div className="progress-fill" style={determinate ? { width: `${progress * 100}%` } : undefined} />
      </div>
      {hint && <p className="hint">{hint}</p>}
    </div>
  );
}
