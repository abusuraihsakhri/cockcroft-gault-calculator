export const MGDL_TO_UMOLL = 88.4;
export const POUNDS_PER_KG = 2.2046226218487757;

function finiteNumber(value, name) {
  const number = Number(value);
  if (!Number.isFinite(number)) throw new Error(name + " must be a finite number.");
  return number;
}

function positiveNumber(value, name) {
  const number = finiteNumber(value, name);
  if (number <= 0) throw new Error(name + " must be greater than zero.");
  return number;
}

function normalizeSex(value) {
  const sex = String(value || "").trim().toUpperCase();
  if (sex !== "M" && sex !== "F") throw new Error("Sex must be M or F.");
  return sex;
}

export function creatinineToMgDl(value, unit) {
  const creatinine = positiveNumber(value, "Creatinine");
  const normalized = String(unit || "").trim().toLowerCase();
  if (["mg/dl", "mgdl", "mg_dl"].includes(normalized)) return creatinine;
  if (["umol/l", "umoll", "umol_l", "micromol/l", "µmol/l"].includes(normalized)) {
    return creatinine / MGDL_TO_UMOLL;
  }
  throw new Error("Unsupported creatinine unit.");
}

export function weightToKg(value, unit) {
  const weight = positiveNumber(value, "Weight");
  const normalized = String(unit || "").trim().toLowerCase();
  if (["kg", "kgs", "kilogram", "kilograms"].includes(normalized)) return weight;
  if (["lb", "lbs", "pound", "pounds"].includes(normalized)) return weight / POUNDS_PER_KG;
  throw new Error("Unsupported weight unit.");
}

export function devineIbw(heightCm, sexValue) {
  const height = positiveNumber(heightCm, "Height");
  const sex = normalizeSex(sexValue);
  const inches = height / 2.54;
  const ibw = (sex === "M" ? 50.0 : 45.5) + 2.3 * (inches - 60.0);
  if (ibw <= 0) throw new Error("Devine IBW is non-positive for this height.");
  return ibw;
}

export function cockcroftGault(ageValue, weightKgValue, creatinineMgDlValue, sexValue) {
  const age = finiteNumber(ageValue, "Age");
  if (age < 18) throw new Error("Cockcroft-Gault is an adult equation; age must be at least 18 years.");
  if (age >= 140) throw new Error("Age must be less than 140 years.");
  const weightKg = positiveNumber(weightKgValue, "Weight");
  const creatinineMgDl = positiveNumber(creatinineMgDlValue, "Creatinine");
  const sex = normalizeSex(sexValue);
  let crcl = ((140 - age) * weightKg) / (72 * creatinineMgDl);
  if (sex === "F") crcl *= 0.85;
  return crcl;
}

export function crclBand(value) {
  const crcl = finiteNumber(value, "CrCl");
  if (crcl < 0) throw new Error("CrCl cannot be negative.");
  if (crcl >= 90) return "≥90 mL/min";
  if (crcl >= 60) return "60–89 mL/min";
  if (crcl >= 30) return "30–59 mL/min";
  if (crcl >= 15) return "15–29 mL/min";
  return "<15 mL/min";
}

export function calculate(input) {
  const weightKg = weightToKg(input.weight, input.weightUnit);
  const creatinineMgDl = creatinineToMgDl(input.creatinine, input.creatinineUnit);
  const age = finiteNumber(input.age, "Age");
  const sex = normalizeSex(input.sex);

  const actualCrCl = cockcroftGault(age, weightKg, creatinineMgDl, sex);
  let ibwKg = null;
  let adjustedKg = null;
  let ibwCrCl = null;
  let adjustedCrCl = null;
  let autoCrCl = actualCrCl;
  let autoBasis = "Actual body weight";
  let note = "";

  if (input.heightCm !== "" && input.heightCm !== null && input.heightCm !== undefined) {
    ibwKg = devineIbw(input.heightCm, sex);
    ibwCrCl = cockcroftGault(age, ibwKg, creatinineMgDl, sex);
    const percentIbw = (weightKg / ibwKg) * 100;
    if (percentIbw > 130) {
      adjustedKg = ibwKg + 0.4 * (weightKg - ibwKg);
      adjustedCrCl = cockcroftGault(age, adjustedKg, creatinineMgDl, sex);
      autoCrCl = adjustedCrCl;
      autoBasis = "Adjusted body weight (>130% IBW heuristic)";
      note = "The adjusted-weight auto-selection is a heuristic. Verify the weight convention required by the current drug label or local protocol.";
    }
  }

  return {
    age,
    sex,
    weightKg,
    creatinineMgDl,
    actualCrCl,
    ibwKg,
    adjustedKg,
    ibwCrCl,
    adjustedCrCl,
    autoCrCl,
    autoBasis,
    band: crclBand(autoCrCl),
    note,
  };
}
