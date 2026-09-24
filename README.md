# Cockcroft–Gault Creatinine Clearance Calculator

### [Open the Live Application →](https://abusuraihsakhri.github.io/cockcroft-gault-calculator/)

A small, dependency-free calculator for estimating adult creatinine clearance (CrCl) with the Cockcroft–Gault equation. The repository includes a Python CLI/library, CSV batch processing, and a compact browser interface.

## Features

- Cockcroft–Gault CrCl using serum creatinine in mg/dL or µmol/L.
- Weight input in kilograms or pounds.
- Optional Devine ideal body weight (IBW) and adjusted body weight (AjBW) estimates when height is supplied.
- Gap-free CrCl reference bands for display only.
- Single-patient CLI and batch CSV processing.
- Static browser application with light/dark theme; calculations stay in the browser.
- Automated Python and browser-logic tests in GitHub Actions.

## Clinical scope and limitations

The implemented equation is:

~~~text
CrCl (male, mL/min)   = [(140 - age) × weight_kg] / [72 × Scr_mg/dL]
CrCl (female, mL/min) = CrCl (male) × 0.85
~~~

The original Cockcroft–Gault publication derived the equation in adults and used a 15% lower estimate for females. This project therefore rejects pediatric ages and mathematically invalid or non-positive inputs.

Weight selection is not universal. When height is supplied, the calculator reports actual-weight and Devine-IBW estimates and retains the historical project heuristic of using AjBW when actual weight exceeds 130% of IBW. That auto-selection is explicitly flagged because the appropriate kidney-function equation, weight convention, and cutoff depend on the drug label or local protocol.

The displayed CrCl bands are **not CKD staging** and do not provide a generic dose recommendation. For clinical dosing, use the current product label and relevant institutional guidance.

References:

- Cockcroft DW, Gault MH. *Prediction of creatinine clearance from serum creatinine.* Nephron. 1976;16(1):31–41. doi:10.1159/000180580.
- NIDDK. *Determining Drug Dosing in Adults with Chronic Kidney Disease.*

## Browser use

Open the live application, enter age, sex, body weight, serum creatinine, and optional height, then select **Calculate**. No data are sent to a server by the application; calculations execute locally in the browser.

The browser interface uses a small JavaScript implementation of the same equations rather than Pyodide. This avoids loading a multi-megabyte Python runtime for a simple calculator while the Python CLI remains the source implementation for command-line and batch workflows.

## Command line

Single patient:

~~~bash
python cli.py single --age 55 --sex M --weight 78.5 --creatinine 1.1 --height-cm 175
~~~

Using pounds and µmol/L:

~~~bash
python cli.py single --age 68 --sex F --weight 137 --weight-unit lbs --creatinine 123.8 --creatinine-unit umol/L --height-cm 160
~~~

Batch CSV:

~~~bash
python cli.py batch -i sample.csv -o results.csv
~~~

Required CSV columns are `patient_id`, `age`, `sex`, `weight_kg`, and `creatinine`. Optional columns are `weight_unit`, `creatinine_unit`, and `height_cm`. Invalid rows are retained in the output with a validation message rather than terminating the full batch.

## Development and tests

Runtime code uses only the Python standard library. Tests require `pytest`; browser calculation tests use Node.js without third-party packages.

~~~bash
python -m pip install pytest
python -m pytest -q
node --test tests/test_web.mjs
python -m compileall -q cockcroft.py cli.py tests
~~~

## Browser compatibility

The web interface targets current versions of Chrome, Edge, Firefox, and Safari with native ES modules enabled.

## License

MIT License. See [LICENSE](LICENSE).
