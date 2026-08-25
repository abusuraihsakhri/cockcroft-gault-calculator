# Cockcroft-Gault Creatinine Clearance Calculator

Estimates creatinine clearance (CrCl) using the Cockcroft-Gault equation, with ideal body weight (IBW) and adjusted body weight calculations for renal drug dosing.

## Equations Implemented

### Cockcroft-Gault
```
CrCl = ((140 - age) × weight_kg) / (72 × Scr_mg_dL)
Multiply by 0.85 for females
```

### Ideal Body Weight (IBW) — Devine Formula
- **Male**: `IBW = 50 + 2.3 × (height_inches - 60)`
- **Female**: `IBW = 45.5 + 2.3 × (height_inches - 60)`

### Adjusted Body Weight
- `AjBW = IBW + 0.4 × (actual_weight - IBW)` — used when actual weight >130% of IBW

### Renal Dosing Categories
| CrCl (mL/min) | Category | Guidance |
|:---:|:---|:---|
| ≥90 | Normal | Standard dosing |
| 60-89 | Mild impairment | Standard dosing; monitor |
| 30-59 | Moderate impairment | Dose reduction/interval extension may be needed |
| 15-29 | Severe impairment | Significant dose reduction required |
| <15 | Kidney failure | May be contraindicated; consider dialysis dosing |

## Usage

```bash
# Single patient
python cockcroft.py single --age 50 --sex M --weight 70 --creatinine 1.0

# With height for IBW calculation
python cockcroft.py single --age 50 --sex F --weight 90 --creatinine 1.2 --height-cm 165

# Batch CSV processing
python cockcroft.py batch --input patients.csv --output results.csv
```

## CSV Input Format

Required: `patient_id`, `age`, `sex`, `weight_kg`, `creatinine`
Optional: `weight_unit` (kg/lb), `creatinine_unit` (mg/dL/umol/L), `height_cm`

## Requirements

Python 3.9+ (stdlib only)

## Disclaimer

For educational and clinical decision support only. Does not replace professional medical judgment. The Cockcroft-Gault equation tends to overestimate CrCl at higher values and may be less accurate in extremes of body weight.
