#!/usr/bin/env python3
"""
Cockcroft-Gault Creatinine Clearance Calculator
================================================

Implements the Cockcroft-Gault equation for estimating creatinine clearance,
with ideal body weight (IBW), adjusted body weight (AjBW), and renal dosing
implications.

    CrCl = ((140 - age) × weight_kg) / (72 × Scr_mg_dL)
    Multiply by 0.85 for females

Stdlib only. Usage: python cockcroft.py --help
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------

MGDL_TO_UMOLL = 88.4


def creatinine_to_mgdl(value: float, unit: str) -> float:
    """Convert a serum creatinine value to mg/dL."""
    unit = unit.strip().lower()
    if unit in ("mg/dl", "mgdl", "mg_dl"):
        return value
    if unit in ("umol/l", "umoll", "umol_l", "micromol/l"):
        return value / MGDL_TO_UMOLL
    raise ValueError(f"Unsupported creatinine unit: {unit!r} (use mg/dL or umol/L)")


def height_to_inches(height_cm: float) -> float:
    """Convert height from cm to inches."""
    return height_cm / 2.54


def weight_to_kg(weight_lbs: float) -> float:
    """Convert weight from pounds to kg."""
    return weight_lbs / 2.205


# ---------------------------------------------------------------------------
# Ideal Body Weight (IBW)
# ---------------------------------------------------------------------------


def ibw_devine(height_inches: float, sex: str) -> float:
    """Devine formula for ideal body weight in kg.

    Male:   IBW = 50 + 2.3 × (height_inches - 60)
    Female: IBW = 45.5 + 2.3 × (height_inches - 60)
    """
    sex = sex.upper()
    if sex == "M":
        return 50.0 + 2.3 * (height_inches - 60)
    elif sex == "F":
        return 45.5 + 2.3 * (height_inches - 60)
    else:
        raise ValueError(f"sex must be 'M' or 'F', got {sex!r}")


def ibw_robinson(height_inches: float, sex: str) -> float:
    """Robinson formula for ideal body weight in kg.

    Male:   IBW = 52 + 1.9 × (height_inches - 60)
    Female: IBW = 49 + 1.7 × (height_inches - 60)
    """
    sex = sex.upper()
    if sex == "M":
        return 52.0 + 1.9 * (height_inches - 60)
    elif sex == "F":
        return 49.0 + 1.7 * (height_inches - 60)
    else:
        raise ValueError(f"sex must be 'M' or 'F', got {sex!r}")


def ibw_miller(height_inches: float, sex: str) -> float:
    """Miller formula for ideal body weight in kg.

    Male:   IBW = 56.2 + 1.41 × (height_inches - 60)
    Female: IBW = 53.1 + 1.36 × (height_inches - 60)
    """
    sex = sex.upper()
    if sex == "M":
        return 56.2 + 1.41 * (height_inches - 60)
    elif sex == "F":
        return 53.1 + 1.36 * (height_inches - 60)
    else:
        raise ValueError(f"sex must be 'M' or 'F', got {sex!r}")


def ibw_hamwi(height_inches: float, sex: str) -> float:
    """Hamwi formula for ideal body weight in kg.

    Male:   IBW = 48 + 2.7 × (height_inches - 60)
    Female: IBW = 45.5 + 2.2 × (height_inches - 60)
    """
    sex = sex.upper()
    if sex == "M":
        return 48.0 + 2.7 * (height_inches - 60)
    elif sex == "F":
        return 45.5 + 2.2 * (height_inches - 60)
    else:
        raise ValueError(f"sex must be 'M' or 'F', got {sex!r}")


# ---------------------------------------------------------------------------
# Adjusted Body Weight
# ---------------------------------------------------------------------------


def adjusted_body_weight(actual_kg: float, ibw_kg: float) -> float:
    """Adjusted body weight = IBW + 0.4 × (actual - IBW).

    Used when actual weight > 130% of IBW.
    """
    return ibw_kg + 0.4 * (actual_kg - ibw_kg)


def percent_ibw(actual_kg: float, ibw_kg: float) -> float:
    """Calculate actual weight as a percentage of IBW."""
    return (actual_kg / ibw_kg) * 100.0


# ---------------------------------------------------------------------------
# Cockcroft-Gault equation
# ---------------------------------------------------------------------------


def cockcroft_gault(age: float, weight_kg: float, scr_mgdl: float, sex: str) -> float:
    """Cockcroft-Gault equation for creatinine clearance (mL/min).

    CrCl = ((140 - age) × weight_kg) / (72 × Scr)
    Multiply by 0.85 for females.
    """
    sex = sex.upper()
    crcl = ((140.0 - age) * weight_kg) / (72.0 * scr_mgdl)
    if sex == "F":
        crcl *= 0.85
    elif sex != "M":
        raise ValueError(f"sex must be 'M' or 'F', got {sex!r}")
    return crcl


# ---------------------------------------------------------------------------
# Renal dosing implications
# ---------------------------------------------------------------------------

DOSING_BANDS = [
    (90.0, float("inf"), "Normal renal function", "Standard dosing"),
    (60.0, 89.99, "Mild impairment", "Standard dosing for most drugs; monitor"),
    (30.0, 59.99, "Moderate impairment", "Dose reduction or interval extension may be needed"),
    (15.0, 29.99, "Severe impairment", "Significant dose reduction required; consult references"),
    (0.0, 14.99, "Kidney failure", "Drug may be contraindicated; consider dialysis dosing"),
]


def renal_dosing_category(crcl: float) -> tuple[str, str]:
    """Return (category, recommendation) for a given CrCl."""
    for low, high, category, recommendation in DOSING_BANDS:
        if low <= crcl <= high:
            return category, recommendation
    return "Kidney failure", "Drug may be contraindicated; consider dialysis dosing"


# ---------------------------------------------------------------------------
# Patient result
# ---------------------------------------------------------------------------


@dataclass
class CrClResult:
    patient_id: str
    age: float
    sex: str
    weight_kg: float
    scr_mgdl: float
    height_inches: Optional[float] = None
    crcl_actual: Optional[float] = None
    crcl_ibw: Optional[float] = None
    crcl_adjusted: Optional[float] = None
    ibw_kg: Optional[float] = None
    adjusted_bw_kg: Optional[float] = None
    percent_ibw: Optional[float] = None
    dosing_category: Optional[str] = None
    dosing_recommendation: Optional[str] = None
    weight_used: str = "actual"
    warnings: list[str] = field(default_factory=list)


def calculate_patient(
    patient_id: str,
    age: float,
    sex: str,
    weight_kg: float,
    scr_mgdl: float,
    height_cm: Optional[float] = None,
) -> CrClResult:
    """Calculate CrCl with all weight adjustments for one patient."""
    sex = sex.upper()
    warnings: list[str] = []

    if age <= 0:
        warnings.append(f"Age {age} must be positive.")
    if weight_kg <= 0:
        warnings.append(f"Weight {weight_kg} must be positive.")
    if scr_mgdl <= 0:
        warnings.append(f"Creatinine {scr_mgdl} must be positive.")

    result = CrClResult(
        patient_id=patient_id, age=age, sex=sex,
        weight_kg=weight_kg, scr_mgdl=scr_mgdl, warnings=warnings,
    )

    # CrCl with actual body weight
    result.crcl_actual = cockcroft_gault(age, weight_kg, scr_mgdl, sex)

    # If height is available, compute IBW and adjusted BW
    if height_cm is not None and height_cm > 0:
        hin = height_to_inches(height_cm)
        result.height_inches = round(hin, 1)
        result.ibw_kg = round(ibw_devine(hin, sex), 1)
        result.percent_ibw = round(percent_ibw(weight_kg, result.ibw_kg), 1)

        if result.percent_ibw > 130:
            result.adjusted_bw_kg = round(adjusted_body_weight(weight_kg, result.ibw_kg), 1)
            result.crcl_adjusted = cockcroft_gault(age, result.adjusted_bw_kg, scr_mgdl, sex)
            result.weight_used = "adjusted"
            result.crcl_ibw = cockcroft_gault(age, result.ibw_kg, scr_mgdl, sex)
        else:
            result.crcl_ibw = cockcroft_gault(age, result.ibw_kg, scr_mgdl, sex)

    # Use the most appropriate CrCl for dosing
    primary_crcl = result.crcl_adjusted if result.crcl_adjusted is not None else result.crcl_actual
    cat, rec = renal_dosing_category(primary_crcl)
    result.dosing_category = cat
    result.dosing_recommendation = rec

    return result


# ---------------------------------------------------------------------------
# CSV batch processing
# ---------------------------------------------------------------------------

CSV_INPUT_FIELDS = [
    "patient_id", "age", "sex", "weight_kg", "weight_unit",
    "creatinine", "creatinine_unit", "height_cm",
]

CSV_OUTPUT_FIELDS = [
    "patient_id", "age", "sex", "weight_kg", "scr_mgdl",
    "height_inches", "ibw_kg", "adjusted_bw_kg", "percent_ibw",
    "crcl_actual", "crcl_ibw", "crcl_adjusted",
    "weight_used", "dosing_category", "dosing_recommendation", "warnings",
]


def _parse_optional_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    return float(value)


def process_csv(input_path: str, output_path: str) -> list[CrClResult]:
    """Read patient rows from CSV, compute CrCl for each, write results CSV."""
    results: list[CrClResult] = []

    with open(input_path, "r", newline="", encoding="utf-8-sig") as f_in:
        reader = csv.DictReader(f_in)
        missing = set(["patient_id", "age", "sex", "weight_kg", "creatinine"]) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Input CSV is missing required columns: {sorted(missing)}")

        for row_num, row in enumerate(reader, start=2):
            patient_id = (row.get("patient_id") or "").strip() or f"row{row_num}"
            row_warnings: list[str] = []

            try:
                age = float(row["age"])
                weight_raw = float(row["weight_kg"])
                scr_raw = float(row["creatinine"])
            except (KeyError, ValueError, TypeError) as exc:
                row_warnings.append(f"Could not parse required fields: {exc}")
                results.append(CrClResult(patient_id=patient_id, age=0, sex="?",
                                           weight_kg=0, scr_mgdl=0, warnings=row_warnings))
                continue

            sex = (row.get("sex") or "").strip().upper()
            weight_unit = (row.get("weight_unit") or "kg").strip().lower()
            creatinine_unit = (row.get("creatinine_unit") or "mg/dL").strip()
            height_cm = _parse_optional_float(row.get("height_cm"))

            if weight_unit in ("lb", "lbs", "pound", "pounds"):
                weight_kg = weight_to_kg(weight_raw)
            else:
                weight_kg = weight_raw

            try:
                scr_mgdl = creatinine_to_mgdl(scr_raw, creatinine_unit)
            except ValueError as exc:
                row_warnings.append(str(exc))
                results.append(CrClResult(patient_id=patient_id, age=age, sex=sex,
                                           weight_kg=weight_kg, scr_mgdl=0, warnings=row_warnings))
                continue

            if sex not in ("M", "F"):
                row_warnings.append(f"Sex must be 'M' or 'F', got {row.get('sex')!r}.")
                results.append(CrClResult(patient_id=patient_id, age=age, sex=sex,
                                           weight_kg=weight_kg, scr_mgdl=scr_mgdl, warnings=row_warnings))
                continue

            result = calculate_patient(
                patient_id=patient_id, age=age, sex=sex,
                weight_kg=weight_kg, scr_mgdl=scr_mgdl, height_cm=height_cm,
            )
            result.warnings = row_warnings + result.warnings
            results.append(result)

    with open(output_path, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=CSV_OUTPUT_FIELDS)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "patient_id": r.patient_id,
                "age": r.age,
                "sex": r.sex,
                "weight_kg": r.weight_kg,
                "scr_mgdl": r.scr_mgdl,
                "height_inches": _fmt(r.height_inches),
                "ibw_kg": _fmt(r.ibw_kg),
                "adjusted_bw_kg": _fmt(r.adjusted_bw_kg),
                "percent_ibw": _fmt(r.percent_ibw),
                "crcl_actual": _fmt(r.crcl_actual),
                "crcl_ibw": _fmt(r.crcl_ibw),
                "crcl_adjusted": _fmt(r.crcl_adjusted),
                "weight_used": r.weight_used,
                "dosing_category": r.dosing_category or "",
                "dosing_recommendation": r.dosing_recommendation or "",
                "warnings": " | ".join(r.warnings),
            })

    return results


def _fmt(value: Optional[float]) -> str:
    return "" if value is None else f"{value:.1f}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cockcroft",
        description="Cockcroft-Gault Creatinine Clearance Calculator with IBW and dosing.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("single", help="Calculate CrCl for one patient")
    single.add_argument("--id", dest="patient_id", default="patient", help="Patient identifier")
    single.add_argument("--age", type=float, required=True, help="Age in years")
    single.add_argument("--sex", required=True, choices=["M", "F", "m", "f"], help="Biological sex")
    single.add_argument("--weight", type=float, required=True, help="Weight in kg")
    single.add_argument("--creatinine", type=float, required=True, help="Serum creatinine value")
    single.add_argument("--creatinine-unit", default="mg/dL",
                        choices=["mg/dL", "mg/dl", "umol/L", "umol/l"],
                        help="Creatinine unit (default: mg/dL)")
    single.add_argument("--height-cm", type=float, default=None, help="Height in cm (optional, for IBW)")

    batch = subparsers.add_parser("batch", help="Batch CSV processing")
    batch.add_argument("-i", "--input", required=True, help="Input CSV path")
    batch.add_argument("-o", "--output", required=True, help="Output CSV path")

    return parser


def _print_single_result(result: CrClResult) -> None:
    print(f"Patient: {result.patient_id}  Age: {result.age}  Sex: {result.sex}")
    print(f"  Weight: {result.weight_kg:.1f} kg  Scr: {result.scr_mgdl:.2f} mg/dL")
    if result.height_inches:
        print(f"  Height: {result.height_inches:.1f} inches")
    if result.ibw_kg:
        print(f"  IBW (Devine): {result.ibw_kg:.1f} kg")
        print(f"  % IBW: {result.percent_ibw:.1f}%")
    if result.adjusted_bw_kg:
        print(f"  Adjusted BW: {result.adjusted_bw_kg:.1f} kg")

    print(f"\n  CrCl (actual BW):   {result.crcl_actual:.1f} mL/min")
    if result.crcl_ibw is not None:
        print(f"  CrCl (IBW):         {result.crcl_ibw:.1f} mL/min")
    if result.crcl_adjusted is not None:
        print(f"  CrCl (adjusted BW): {result.crcl_adjusted:.1f} mL/min")

    print(f"\n  Recommended weight for dosing: {result.weight_used}")
    print(f"  Renal function: {result.dosing_category}")
    print(f"  Dosing guidance: {result.dosing_recommendation}")

    if result.warnings:
        print("\n  Warnings:")
        for w in result.warnings:
            print(f"    - {w}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "single":
        try:
            scr_mgdl = creatinine_to_mgdl(args.creatinine, args.creatinine_unit)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        result = calculate_patient(
            patient_id=args.patient_id, age=args.age, sex=args.sex,
            weight_kg=args.weight, scr_mgdl=scr_mgdl, height_cm=args.height_cm,
        )
        _print_single_result(result)
        return 0

    if args.command == "batch":
        results = process_csv(args.input, args.output)
        n_warned = sum(1 for r in results if r.warnings)
        print(f"Processed {len(results)} patients -> {args.output}")
        if n_warned:
            print(f"{n_warned} patient(s) had warnings.")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
