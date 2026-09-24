#!/usr/bin/env python3
"""Cockcroft-Gault creatinine-clearance calculator.

Implements the 1976 Cockcroft-Gault equation and optional Devine ideal-body-
weight / adjusted-body-weight estimates. The module is dependency-free and is
usable both as a library and from the command line.

The calculator reports estimates. Drug dosing must follow the method and
thresholds in the relevant current product label or local protocol.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass, field
from typing import Optional

MGDL_TO_UMOLL = 88.4
POUNDS_PER_KG = 2.2046226218487757


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    return value


def _positive(value: float, name: str) -> float:
    value = _finite(value, name)
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return value


def _normalise_sex(sex: str) -> str:
    normalised = str(sex).strip().upper()
    if normalised not in {"M", "F"}:
        raise ValueError(f"sex must be 'M' or 'F', got {sex!r}")
    return normalised


def creatinine_to_mgdl(value: float, unit: str) -> float:
    """Convert a positive serum-creatinine value to mg/dL."""
    value = _positive(value, "Creatinine")
    unit_normalised = str(unit).strip().lower()
    if unit_normalised in {"mg/dl", "mgdl", "mg_dl"}:
        return value
    if unit_normalised in {"umol/l", "umoll", "umol_l", "micromol/l", "µmol/l"}:
        return value / MGDL_TO_UMOLL
    raise ValueError(f"Unsupported creatinine unit: {unit!r} (use mg/dL or umol/L)")


def height_to_inches(height_cm: float) -> float:
    """Convert a positive height from centimetres to inches."""
    return _positive(height_cm, "Height") / 2.54


def weight_to_kg(weight_lbs: float) -> float:
    """Convert a positive weight from pounds to kilograms."""
    return _positive(weight_lbs, "Weight") / POUNDS_PER_KG


def ibw_devine(height_inches: float, sex: str) -> float:
    """Return Devine ideal body weight (kg)."""
    height_inches = _positive(height_inches, "Height")
    sex = _normalise_sex(sex)
    result = (50.0 if sex == "M" else 45.5) + 2.3 * (height_inches - 60.0)
    if result <= 0:
        raise ValueError("Devine IBW is non-positive for this height; do not use this estimate.")
    return result


def ibw_robinson(height_inches: float, sex: str) -> float:
    """Return Robinson ideal body weight (kg)."""
    height_inches = _positive(height_inches, "Height")
    sex = _normalise_sex(sex)
    if sex == "M":
        result = 52.0 + 1.9 * (height_inches - 60.0)
    else:
        result = 49.0 + 1.7 * (height_inches - 60.0)
    if result <= 0:
        raise ValueError("Robinson IBW is non-positive for this height; do not use this estimate.")
    return result


def ibw_miller(height_inches: float, sex: str) -> float:
    """Return Miller ideal body weight (kg)."""
    height_inches = _positive(height_inches, "Height")
    sex = _normalise_sex(sex)
    if sex == "M":
        result = 56.2 + 1.41 * (height_inches - 60.0)
    else:
        result = 53.1 + 1.36 * (height_inches - 60.0)
    if result <= 0:
        raise ValueError("Miller IBW is non-positive for this height; do not use this estimate.")
    return result


def ibw_hamwi(height_inches: float, sex: str) -> float:
    """Return Hamwi ideal body weight (kg)."""
    height_inches = _positive(height_inches, "Height")
    sex = _normalise_sex(sex)
    if sex == "M":
        result = 48.0 + 2.7 * (height_inches - 60.0)
    else:
        result = 45.5 + 2.2 * (height_inches - 60.0)
    if result <= 0:
        raise ValueError("Hamwi IBW is non-positive for this height; do not use this estimate.")
    return result


def adjusted_body_weight(actual_kg: float, ibw_kg: float) -> float:
    """Return adjusted body weight: IBW + 0.4 × (actual - IBW)."""
    actual_kg = _positive(actual_kg, "Actual weight")
    ibw_kg = _positive(ibw_kg, "IBW")
    return ibw_kg + 0.4 * (actual_kg - ibw_kg)


def percent_ibw(actual_kg: float, ibw_kg: float) -> float:
    """Return actual body weight as a percentage of IBW."""
    actual_kg = _positive(actual_kg, "Actual weight")
    ibw_kg = _positive(ibw_kg, "IBW")
    return (actual_kg / ibw_kg) * 100.0


def cockcroft_gault(age: float, weight_kg: float, scr_mgdl: float, sex: str) -> float:
    """Estimate creatinine clearance in mL/min with Cockcroft-Gault.

    Adult ages from 18 to less than 140 years are accepted. The upper bound
    prevents mathematically invalid negative clearances from the (140 - age)
    term; the equation was originally derived in adults.
    """
    age = _finite(age, "Age")
    if age < 18:
        raise ValueError("Cockcroft-Gault is an adult equation; age must be at least 18 years.")
    if age >= 140:
        raise ValueError("Age must be less than 140 years for Cockcroft-Gault.")
    weight_kg = _positive(weight_kg, "Weight")
    scr_mgdl = _positive(scr_mgdl, "Creatinine")
    sex = _normalise_sex(sex)

    crcl = ((140.0 - age) * weight_kg) / (72.0 * scr_mgdl)
    if sex == "F":
        crcl *= 0.85
    return crcl


REFERENCE_BANDS = (
    (90.0, "≥90 mL/min"),
    (60.0, "60–89 mL/min"),
    (30.0, "30–59 mL/min"),
    (15.0, "15–29 mL/min"),
    (0.0, "<15 mL/min"),
)

DRUG_SPECIFIC_NOTE = (
    "Use the kidney-function method and cutoff specified in the current drug label "
    "or local dosing protocol; no generic dose adjustment is inferred from this band."
)


def renal_dosing_category(crcl: float) -> tuple[str, str]:
    """Return a gap-free CrCl reference band and a non-prescriptive dosing note.

    The historical function name is retained for API compatibility. The bands
    are descriptive only and must not be treated as CKD staging or as a generic
    drug-dosing rule.
    """
    crcl = _finite(crcl, "CrCl")
    if crcl < 0:
        raise ValueError("CrCl cannot be negative.")
    for lower_bound, label in REFERENCE_BANDS:
        if crcl >= lower_bound:
            return label, DRUG_SPECIFIC_NOTE
    raise RuntimeError("Unreachable reference-band state")


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
    """Calculate Cockcroft-Gault estimates for one adult patient.

    Actual-body-weight CrCl is always calculated. If height is supplied,
    Devine IBW and an adjusted-body-weight estimate are also calculated. The
    historical >130% IBW auto-selection heuristic is retained for compatibility
    but is explicitly flagged because weight choice is protocol- and drug-
    specific.
    """
    age = _finite(age, "Age")
    sex = _normalise_sex(sex)
    weight_kg = _positive(weight_kg, "Weight")
    scr_mgdl = _positive(scr_mgdl, "Creatinine")

    result = CrClResult(
        patient_id=str(patient_id),
        age=age,
        sex=sex,
        weight_kg=weight_kg,
        scr_mgdl=scr_mgdl,
    )
    result.crcl_actual = cockcroft_gault(age, weight_kg, scr_mgdl, sex)

    if height_cm is not None:
        height_cm = _positive(height_cm, "Height")
        hin = height_to_inches(height_cm)
        ibw = ibw_devine(hin, sex)
        pct_ibw = percent_ibw(weight_kg, ibw)

        result.height_inches = round(hin, 1)
        result.ibw_kg = round(ibw, 1)
        result.percent_ibw = round(pct_ibw, 1)
        result.crcl_ibw = cockcroft_gault(age, ibw, scr_mgdl, sex)

        if pct_ibw > 130.0:
            adjusted = adjusted_body_weight(weight_kg, ibw)
            result.adjusted_bw_kg = round(adjusted, 1)
            result.crcl_adjusted = cockcroft_gault(age, adjusted, scr_mgdl, sex)
            result.weight_used = "adjusted"
            result.warnings.append(
                "Adjusted body weight was auto-selected by the >130% IBW heuristic; "
                "verify the weight convention required by the drug label or local protocol."
            )

    primary_crcl = result.crcl_adjusted if result.crcl_adjusted is not None else result.crcl_actual
    if primary_crcl is None:
        raise RuntimeError("Primary CrCl was not calculated")
    category, note = renal_dosing_category(primary_crcl)
    result.dosing_category = category
    result.dosing_recommendation = note
    return result


CSV_INPUT_FIELDS = [
    "patient_id",
    "age",
    "sex",
    "weight_kg",
    "weight_unit",
    "creatinine",
    "creatinine_unit",
    "height_cm",
]

CSV_OUTPUT_FIELDS = [
    "patient_id",
    "age",
    "sex",
    "weight_kg",
    "scr_mgdl",
    "height_inches",
    "ibw_kg",
    "adjusted_bw_kg",
    "percent_ibw",
    "crcl_actual",
    "crcl_ibw",
    "crcl_adjusted",
    "weight_used",
    "dosing_category",
    "dosing_recommendation",
    "warnings",
]


def _parse_optional_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    return float(value)


def _invalid_result(
    patient_id: str,
    message: str,
    *,
    age: float = 0.0,
    sex: str = "?",
    weight_kg: float = 0.0,
    scr_mgdl: float = 0.0,
) -> CrClResult:
    return CrClResult(
        patient_id=patient_id,
        age=age,
        sex=sex,
        weight_kg=weight_kg,
        scr_mgdl=scr_mgdl,
        warnings=[message],
    )


def process_csv(input_path: str, output_path: str) -> list[CrClResult]:
    """Process a CSV cohort; invalid rows are reported instead of aborting the batch."""
    results: list[CrClResult] = []

    with open(input_path, "r", newline="", encoding="utf-8-sig") as f_in:
        reader = csv.DictReader(f_in)
        required = {"patient_id", "age", "sex", "weight_kg", "creatinine"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Input CSV is missing required columns: {sorted(missing)}")

        for row_num, row in enumerate(reader, start=2):
            patient_id = (row.get("patient_id") or "").strip() or f"row{row_num}"

            try:
                age = float(row["age"])
                weight_raw = float(row["weight_kg"])
                scr_raw = float(row["creatinine"])
            except (KeyError, TypeError, ValueError) as exc:
                results.append(_invalid_result(patient_id, f"Could not parse required fields: {exc}"))
                continue

            sex = (row.get("sex") or "").strip().upper()
            weight_unit = (row.get("weight_unit") or "kg").strip().lower()
            creatinine_unit = (row.get("creatinine_unit") or "mg/dL").strip()
            weight_kg = 0.0
            scr_mgdl = 0.0

            try:
                if weight_unit in {"kg", "kgs", "kilogram", "kilograms"}:
                    weight_kg = _positive(weight_raw, "Weight")
                elif weight_unit in {"lb", "lbs", "pound", "pounds"}:
                    weight_kg = weight_to_kg(weight_raw)
                else:
                    raise ValueError(f"Unsupported weight unit: {weight_unit!r} (use kg or lbs)")

                scr_mgdl = creatinine_to_mgdl(scr_raw, creatinine_unit)
                height_cm = _parse_optional_float(row.get("height_cm"))
                result = calculate_patient(
                    patient_id=patient_id,
                    age=age,
                    sex=sex,
                    weight_kg=weight_kg,
                    scr_mgdl=scr_mgdl,
                    height_cm=height_cm,
                )
            except (TypeError, ValueError) as exc:
                safe_weight = weight_kg if math.isfinite(weight_kg) else 0.0
                safe_scr = scr_mgdl if math.isfinite(scr_mgdl) else 0.0
                results.append(
                    _invalid_result(
                        patient_id,
                        str(exc),
                        age=age,
                        sex=sex or "?",
                        weight_kg=safe_weight,
                        scr_mgdl=safe_scr,
                    )
                )
                continue

            results.append(result)

    with open(output_path, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=CSV_OUTPUT_FIELDS)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "patient_id": result.patient_id,
                    "age": result.age,
                    "sex": result.sex,
                    "weight_kg": _fmt(result.weight_kg),
                    "scr_mgdl": _fmt(result.scr_mgdl),
                    "height_inches": _fmt(result.height_inches),
                    "ibw_kg": _fmt(result.ibw_kg),
                    "adjusted_bw_kg": _fmt(result.adjusted_bw_kg),
                    "percent_ibw": _fmt(result.percent_ibw),
                    "crcl_actual": _fmt(result.crcl_actual),
                    "crcl_ibw": _fmt(result.crcl_ibw),
                    "crcl_adjusted": _fmt(result.crcl_adjusted),
                    "weight_used": result.weight_used,
                    "dosing_category": result.dosing_category or "",
                    "dosing_recommendation": result.dosing_recommendation or "",
                    "warnings": " | ".join(result.warnings),
                }
            )

    return results


def _fmt(value: Optional[float]) -> str:
    return "" if value is None else f"{value:.1f}"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cockcroft",
        description="Cockcroft-Gault creatinine-clearance calculator.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("single", help="Calculate CrCl for one adult")
    single.add_argument("--id", dest="patient_id", default="patient", help="Patient identifier")
    single.add_argument("--age", type=float, required=True, help="Age in years (adult)")
    single.add_argument("--sex", required=True, choices=["M", "F", "m", "f"], help="Sex used by the original equation")
    single.add_argument("--weight", type=float, required=True, help="Body weight")
    single.add_argument("--weight-unit", default="kg", choices=["kg", "lb", "lbs"], help="Weight unit (default: kg)")
    single.add_argument("--creatinine", type=float, required=True, help="Serum creatinine")
    single.add_argument(
        "--creatinine-unit",
        default="mg/dL",
        choices=["mg/dL", "mg/dl", "umol/L", "umol/l"],
        help="Creatinine unit (default: mg/dL)",
    )
    single.add_argument("--height-cm", type=float, default=None, help="Height in cm (optional)")

    batch = subparsers.add_parser("batch", help="Process a CSV cohort")
    batch.add_argument("-i", "--input", required=True, help="Input CSV path")
    batch.add_argument("-o", "--output", required=True, help="Output CSV path")
    return parser


def _print_single_result(result: CrClResult) -> None:
    print(f"Patient: {result.patient_id}  Age: {result.age:g}  Sex: {result.sex}")
    print(f"  Weight: {result.weight_kg:.1f} kg  Scr: {result.scr_mgdl:.2f} mg/dL")
    if result.height_inches is not None:
        print(f"  Height: {result.height_inches:.1f} inches")
    if result.ibw_kg is not None:
        print(f"  IBW (Devine): {result.ibw_kg:.1f} kg")
        print(f"  % IBW: {result.percent_ibw:.1f}%")
    if result.adjusted_bw_kg is not None:
        print(f"  Adjusted BW: {result.adjusted_bw_kg:.1f} kg")

    print(f"\n  CrCl (actual BW):   {result.crcl_actual:.1f} mL/min")
    if result.crcl_ibw is not None:
        print(f"  CrCl (IBW):         {result.crcl_ibw:.1f} mL/min")
    if result.crcl_adjusted is not None:
        print(f"  CrCl (adjusted BW): {result.crcl_adjusted:.1f} mL/min")

    print(f"\n  Auto-selected weight basis: {result.weight_used}")
    print(f"  CrCl reference band: {result.dosing_category}")
    print(f"  Dosing note: {result.dosing_recommendation}")
    if result.warnings:
        print("\n  Notes:")
        for warning in result.warnings:
            print(f"    - {warning}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "single":
        try:
            weight_kg = args.weight if args.weight_unit == "kg" else weight_to_kg(args.weight)
            scr_mgdl = creatinine_to_mgdl(args.creatinine, args.creatinine_unit)
            result = calculate_patient(
                patient_id=args.patient_id,
                age=args.age,
                sex=args.sex,
                weight_kg=weight_kg,
                scr_mgdl=scr_mgdl,
                height_cm=args.height_cm,
            )
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        _print_single_result(result)
        return 0

    if args.command == "batch":
        try:
            results = process_csv(args.input, args.output)
        except (OSError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        n_warned = sum(1 for result in results if result.warnings)
        print(f"Processed {len(results)} patients -> {args.output}")
        if n_warned:
            print(f"{n_warned} patient(s) had notes or validation errors.")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
