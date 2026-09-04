# Cockcroft-Gault Creatinine Clearance Calculator

A robust clinical computing tool implementing the Cockcroft-Gault equation for estimating creatinine clearance (CrCl), comprehensive Ideal Body Weight (IBW) and Adjusted Body Weight (AjBW) models, and renal drug dose adjustment stratification.

---

## Clinical Domain & Mathematical Principles

The Cockcroft-Gault formula (1976) remains one of the primary clinical standards for evaluating renal elimination capacity and calculating drug dose adjustments (e.g., direct oral anticoagulants, aminoglycosides, glycopeptides, chemotherapeutic regimens).

### 1. Primary Cockcroft-Gault Equation

```text
CrCl (male, mL/min)   = [(140 - age) * weight_kg] / [72 * Scr_mg_dL]
CrCl (female, mL/min) = CrCl (male) * 0.85
```

When serum creatinine is reported in umol/L, conversion to mg/dL is performed:
```text
Scr (mg/dL) = Scr (umol/L) / 88.4
```

---

### 2. Ideal Body Weight (IBW) Formulations

Body composition significantly affects serum creatinine generation. The calculator supports standard formulas based on height in inches (height_in = height_cm / 2.54):

| Method | Male IBW (kg) | Female IBW (kg) |
|:-------|:--------------|:----------------|
| **Devine (1974)** *(Default)* | 50.0 + 2.3 * (height_in - 60) | 45.5 + 2.3 * (height_in - 60) |
| **Robinson (1983)** | 52.0 + 1.9 * (height_in - 60) | 49.0 + 1.7 * (height_in - 60) |
| **Miller (1983)** | 56.2 + 1.41 * (height_in - 60) | 53.1 + 1.36 * (height_in - 60) |
| **Hamwi (1964)** | 48.0 + 2.7 * (height_in - 60) | 45.5 + 2.2 * (height_in - 60) |

---

### 3. Weight Selection Algorithm & Adjusted Body Weight (AjBW)

In obesity, using actual body weight substantially overestimates clearance due to inactive adipose tissue mass, while using IBW underestimates clearance due to renal hypertrophy.

```text
% IBW = (Weight_actual / IBW) * 100
AjBW (kg) = IBW + 0.4 * (Weight_actual - IBW)
```

```
+-------------------------------------------------------------+
|                Weight Selection Decision Rule               |
+-------------------------------------------------------------+
| Actual Weight < IBW:       Use Actual Body Weight           |
| Actual Weight 100% - 130%: Use Actual Body Weight           |
| Actual Weight > 130% IBW:  Use Adjusted Body Weight (AjBW)  |
+-------------------------------------------------------------+
```

---

### 4. Renal Function Stratification & Dose Guidance

```
+----------------+---------------------+---------------------------------------------------+
| CrCl (mL/min)  | Stage / Category    | Clinical Pharmacotherapy Guidance                 |
+----------------+---------------------+---------------------------------------------------+
| >= 90          | Normal function     | Standard adult dosing                             |
| 60 - 89        | Mild impairment     | Standard dosing for most drugs; monitor           |
| 30 - 59        | Moderate impairment | Dose reduction or interval extension may be needed|
| 15 - 29        | Severe impairment   | Significant dose reduction required; consult ref  |
| < 15           | Kidney failure      | Dialysis-dependent; strict clearance dosing       |
+----------------+---------------------+---------------------------------------------------+
```

---

## CLI Quickstart & Usage

The application provides a command-line interface via `cli.py` (or `cockcroft.py`) supporting both single-patient calculations and high-throughput batch CSV processing.

### 1. Single Patient Mode

Calculate clearance for a single patient with optional height for IBW and AjBW:

```bash
# Standard calculation (mg/dL)
python cli.py single --age 55 --sex M --weight 78.5 --creatinine 1.1

# Calculation with height (cm) and SI units (umol/L)
python cli.py single --age 68 --sex F --weight 62 --creatinine 123.8 --creatinine-unit umol/L --height-cm 160
```

### 2. Batch CSV Processing

Process multi-patient cohorts with automatic weight adjustment and clinical risk categorization:

```bash
# Short flags (-i, -o)
python cli.py batch -i sample.csv -o results.csv

# Long flags (--input, --output)
python cli.py batch --input sample.csv --output results.csv
```

### Batch Input Schema (`sample.csv`)

| Column Name | Type | Description | Example |
|:------------|:-----|:------------|:--------|
| `patient_id` | string | Unique patient / specimen identifier | `PT001` |
| `age` | float | Age in years | `55` |
| `sex` | char | Biological sex (`M` or `F`) | `M` |
| `weight_kg` | float | Measured weight | `78.5` |
| `weight_unit` | string | Unit: `kg` or `lbs` (default: `kg`) | `kg` |
| `creatinine` | float | Serum creatinine value | `1.1` |
| `creatinine_unit` | string | Unit: `mg/dL` or `umol/L` (default: `mg/dL`) | `mg/dL` |
| `height_cm` | float (optional) | Height in cm for IBW / AjBW calculation | `175` |

---

## Testing & Verification

Run the full automated test suite:

```bash
python -m pytest -p no:zarr -v
```

Execute batch CLI smoke verification:

```bash
python cli.py batch -i sample.csv -o out_smoke.csv
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
