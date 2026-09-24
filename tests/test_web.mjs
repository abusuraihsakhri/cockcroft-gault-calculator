import test from "node:test";
import assert from "node:assert/strict";
import { calculate, cockcroftGault, crclBand, creatinineToMgDl, weightToKg } from "../web/calc.mjs";

test("Cockcroft-Gault male reference calculation", () => {
  assert.ok(Math.abs(cockcroftGault(50, 70, 1, "M") - 87.5) < 0.001);
});

test("female factor", () => {
  assert.ok(Math.abs(cockcroftGault(50, 60, 1, "F") - 63.75) < 0.001);
});

test("unit conversions", () => {
  assert.ok(Math.abs(creatinineToMgDl(88.4, "umol/L") - 1) < 0.001);
  assert.ok(Math.abs(weightToKg(154, "lbs") - 69.853) < 0.05);
});

test("reference bands have no decimal gaps", () => {
  assert.equal(crclBand(89.999), "60–89 mL/min");
  assert.equal(crclBand(59.999), "30–59 mL/min");
  assert.equal(crclBand(29.999), "15–29 mL/min");
  assert.equal(crclBand(14.999), "<15 mL/min");
});

test("calculator exposes adjusted-weight heuristic without hiding alternatives", () => {
  const result = calculate({
    age: 50,
    sex: "M",
    weight: 120,
    weightUnit: "kg",
    creatinine: 1,
    creatinineUnit: "mg/dL",
    heightCm: 170,
  });
  assert.ok(result.actualCrCl > 0);
  assert.ok(result.ibwCrCl > 0);
  assert.ok(result.adjustedCrCl > 0);
  assert.match(result.autoBasis, /Adjusted body weight/);
  assert.match(result.note, /heuristic/);
});

test("invalid inputs are rejected", () => {
  assert.throws(() => cockcroftGault(17, 70, 1, "M"), /adult equation/);
  assert.throws(() => cockcroftGault(50, 70, 0, "M"), /greater than zero/);
});
