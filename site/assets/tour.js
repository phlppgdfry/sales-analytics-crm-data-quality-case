// Guided tour (2 minutes) for the prototype: "Step x of y", Back / Next / Close.
// Usage in the prototype:
//   import { createTour } from "../assets/tour.js";
//   const tour = createTour([
//     { text: "What the viewer sees and why it matters.", focus: "#list", before: () => selectOrder("A-1") },
//     ...6–10 steps along the killer flow...
//   Story arc: problem → key decision(s) → demonstration → result → limitations.
//   The last step says what is simulated and what this case does not show.
//   ]);
//   document.querySelector("#btn-tour").addEventListener("click", () => tour.start());
// Opening the page with ?tour starts it automatically, so the CV/README link can be <demo-url>?tour.
// Needs the markup below once on the page (or let createTour inject it):
//   <div class="tour hidden" id="tour" role="dialog" aria-label="Guided tour">…</div>
// Labels default to English; pass { labels: { step: "Stap", of: "van", back: "Terug", next: "Volgende", finish: "Klaar", close: "Sluiten" } } for Dutch.

const EN = { step: "Step", of: "of", back: "Back", next: "Next", finish: "Finish", close: "Close" };

export function createTour(steps, { label = "Guided tour", labels = {} } = {}) {
  const L = { ...EN, ...labels };
  let box = document.getElementById("tour");
  if (!box) {
    box = document.createElement("div");
    box.id = "tour";
    box.className = "tour hidden";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-label", label);
    box.innerHTML = `<p id="tour-text" aria-live="polite"></p>
      <div class="tour-actions">
        <button type="button" data-tour="prev">${L.back}</button>
        <button type="button" data-tour="next">${L.next}</button>
        <button type="button" data-tour="close">${L.close}</button>
      </div>`;
    document.body.appendChild(box);
  }
  const text = box.querySelector("#tour-text");
  const prev = box.querySelector('[data-tour="prev"]');
  const next = box.querySelector('[data-tour="next"]');
  let current = -1;

  function show(i) {
    if (i < 0 || i >= steps.length) {
      box.classList.add("hidden");
      current = -1;
      return;
    }
    current = i;
    const step = steps[i];
    if (step.before) step.before();
    box.classList.remove("hidden");
    text.textContent = "";
    const counter = document.createElement("span");
    counter.className = "tour-step";
    counter.textContent = `${L.step} ${i + 1} ${L.of} ${steps.length}`;
    text.append(counter, step.text);
    prev.disabled = i === 0;
    next.textContent = i === steps.length - 1 ? L.finish : L.next;
    const el = step.focus && document.querySelector(step.focus);
    if (el) {
      el.classList.remove("tour-flash");
      void el.offsetWidth; // restart the highlight animation
      el.classList.add("tour-flash");
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  prev.addEventListener("click", () => show(Math.max(0, current - 1)));
  next.addEventListener("click", () => show(current + 1));
  box.querySelector('[data-tour="close"]').addEventListener("click", () => show(-1));
  document.addEventListener("keydown", (e) => {
    if (current < 0) return;
    if (e.key === "Escape") show(-1);
    if (e.key === "ArrowRight") show(current + 1);
    if (e.key === "ArrowLeft" && current > 0) show(current - 1);
  });

  const tour = { start: () => show(0), stop: () => show(-1), show };
  if (new URLSearchParams(location.search).has("tour")) {
    // let the prototype render first; setTimeout also fires in background tabs, where requestAnimationFrame does not
    setTimeout(() => tour.start(), 0);
  }
  return tour;
}
