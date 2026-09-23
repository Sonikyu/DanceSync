import { useId, useRef } from "react";
import { nextOption } from "../flow.js";

const ARROW_STEPS = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };

// A labelled row of mutually exclusive options: a radio group drawn as a
// pill. It holds no state; the parent owns `value`. Like a native radio
// group it's one tab stop, and the arrow keys move the choice, skipping
// disabled options. `options` is [{ value, label, disabled }].
export default function Segmented({ label, options, value, onChange }) {
  const labelId = useId();
  const groupRef = useRef(null);
  const focusable = options.some((option) => option.value === value) ? value : options[0].value;

  function onKeyDown(event) {
    const step = ARROW_STEPS[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const next = nextOption(options, value, step);
    if (next === null) return;
    onChange(next);
    groupRef.current.querySelector(`[data-value="${next}"]`).focus();
  }

  return (
    <div className="control">
      <span className="hint" id={labelId}>{label}</span>
      <div className="segmented" role="radiogroup" aria-labelledby={labelId} ref={groupRef} onKeyDown={onKeyDown}>
        {options.map((option) => (
          <button
            key={option.value}
            role="radio"
            data-value={option.value}
            aria-checked={value === option.value}
            tabIndex={focusable === option.value ? 0 : -1}
            disabled={option.disabled}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
