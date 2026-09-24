import { calculate } from "./calc.mjs";

const form = document.querySelector("#calculator-form");
const resultPanel = document.querySelector("#result-panel");
const emptyState = document.querySelector("#empty-state");
const errorBox = document.querySelector("#error-box");
const themeButton = document.querySelector("#theme-toggle");

function format(value, digits = 1) {
  return Number(value).toFixed(digits);
}

function setText(id, text) {
  document.querySelector(id).textContent = text;
}

function render(result) {
  errorBox.hidden = true;
  emptyState.hidden = true;
  resultPanel.hidden = false;

  setText("#primary-crcl", format(result.autoCrCl) + " mL/min");
  setText("#primary-basis", result.autoBasis);
  setText("#band", result.band);
  setText("#actual-crcl", format(result.actualCrCl));
  setText("#actual-crcl-copy", format(result.actualCrCl));
  setText("#scr-mgdl", format(result.creatinineMgDl, 2));
  setText("#weight-kg", format(result.weightKg));

  const ibwRow = document.querySelector("#ibw-row");
  const adjustedRow = document.querySelector("#adjusted-row");
  if (result.ibwCrCl !== null) {
    ibwRow.hidden = false;
    setText("#ibw-crcl", format(result.ibwCrCl));
    setText("#ibw-weight", format(result.ibwKg));
  } else {
    ibwRow.hidden = true;
  }

  if (result.adjustedCrCl !== null) {
    adjustedRow.hidden = false;
    setText("#adjusted-crcl", format(result.adjustedCrCl));
    setText("#adjusted-weight", format(result.adjustedKg));
  } else {
    adjustedRow.hidden = true;
  }

  const note = document.querySelector("#selection-note");
  note.textContent = result.note;
  note.hidden = !result.note;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  try {
    const data = new FormData(form);
    const result = calculate({
      age: data.get("age"),
      sex: data.get("sex"),
      weight: data.get("weight"),
      weightUnit: data.get("weightUnit"),
      creatinine: data.get("creatinine"),
      creatinineUnit: data.get("creatinineUnit"),
      heightCm: data.get("heightCm"),
    });
    render(result);
  } catch (error) {
    resultPanel.hidden = true;
    emptyState.hidden = true;
    errorBox.hidden = false;
    errorBox.textContent = error instanceof Error ? error.message : String(error);
  }
});

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeButton.setAttribute("aria-label", theme === "dark" ? "Use light theme" : "Use dark theme");
  themeButton.textContent = theme === "dark" ? "☀" : "☾";
  localStorage.setItem("cg-theme", theme);
}

const storedTheme = localStorage.getItem("cg-theme");
const preferredDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
applyTheme(storedTheme || (preferredDark ? "dark" : "light"));

themeButton.addEventListener("click", () => {
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
});
