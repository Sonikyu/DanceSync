import { STAGES } from "../flow.js";

export default function StepDots({ current }) {
  return (
    <ol className="dots" aria-label={`Step ${current + 1} of ${STAGES.length}: ${STAGES[current]}`}>
      {STAGES.map((name, index) => (
        <li key={name} className={dotClass(index, current)} />
      ))}
    </ol>
  );
}

function dotClass(index, current) {
  if (index === current) return "dot current";
  return index < current ? "dot done" : "dot";
}
