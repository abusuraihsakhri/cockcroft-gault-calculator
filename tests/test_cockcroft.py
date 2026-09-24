import csv
import math
import os
import tempfile

import pytest

import cockcroft as cg


def test_cg_male_basic():
    result = cg.cockcroft_gault(age=50, weight_kg=70, scr_mgdl=1.0, sex="M")
    assert math.isclose(result, 87.5, abs_tol=0.01)


def test_cg_female_basic():
    result = cg.cockcroft_gault(age=50, weight_kg=60, scr_mgdl=1.0, sex="F")
    assert math.isclose(result, 63.75, abs_tol=0.01)


def test_cg_rejects_invalid_inputs():
    for kwargs in (
        {"age": 17, "weight_kg": 70, "scr_mgdl": 1.0, "sex": "M"},
        {"age": 140, "weight_kg": 70, "scr_mgdl": 1.0, "sex": "M"},
        {"age": 50, "weight_kg": 0, "scr_mgdl": 1.0, "sex": "M"},
        {"age": 50, "weight_kg": 70, "scr_mgdl": 0, "sex": "M"},
        {"age": 50, "weight_kg": 70, "scr_mgdl": float("nan"), "sex": "M"},
        {"age": 50, "weight_kg": 70, "scr_mgdl": 1.0, "sex": "X"},
    ):
        with pytest.raises(ValueError):
            cg.cockcroft_gault(**kwargs)


def test_ibw_formulas():
    assert math.isclose(cg.ibw_devine(70, "M"), 73.0, abs_tol=0.01)
    assert math.isclose(cg.ibw_devine(64, "F"), 54.7, abs_tol=0.01)
    assert math.isclose(cg.ibw_robinson(70, "M"), 71.0, abs_tol=0.01)
    assert math.isclose(cg.ibw_miller(70, "M"), 70.3, abs_tol=0.01)
    assert math.isclose(cg.ibw_hamwi(70, "M"), 75.0, abs_tol=0.01)


def test_conversion_functions():
    assert math.isclose(cg.creatinine_to_mgdl(88.4, "umol/L"), 1.0, abs_tol=0.01)
    assert math.isclose(cg.height_to_inches(177.8), 70.0, abs_tol=0.01)
    assert math.isclose(cg.weight_to_kg(154), 69.853, abs_tol=0.05)
    with pytest.raises(ValueError):
        cg.creatinine_to_mgdl(1.0, "mg/L")


def test_adjusted_body_weight_and_percent_ibw():
    assert math.isclose(cg.adjusted_body_weight(100, 70), 82.0, abs_tol=0.01)
    assert math.isclose(cg.percent_ibw(100, 70), 142.857, abs_tol=0.01)


@pytest.mark.parametrize(
    ("crcl", "expected"),
    [
        (120, "≥90 mL/min"),
        (90, "≥90 mL/min"),
        (89.999, "60–89 mL/min"),
        (60, "60–89 mL/min"),
        (59.999, "30–59 mL/min"),
        (30, "30–59 mL/min"),
        (29.999, "15–29 mL/min"),
        (15, "15–29 mL/min"),
        (14.999, "<15 mL/min"),
        (0, "<15 mL/min"),
    ],
)
def test_reference_bands_have_no_gaps(crcl, expected):
    label, note = cg.renal_dosing_category(crcl)
    assert label == expected
    assert "drug label" in note.lower()


def test_calculate_patient_with_height_and_obesity_note():
    result = cg.calculate_patient("P2", 50, "M", 120, 1.0, height_cm=170)
    assert result.ibw_kg is not None
    assert result.percent_ibw > 130
    assert result.adjusted_bw_kg is not None
    assert result.crcl_adjusted is not None
    assert result.weight_used == "adjusted"
    assert any("heuristic" in warning for warning in result.warnings)


def test_calculate_patient_normal_weight_uses_actual():
    result = cg.calculate_patient("P3", 40, "F", 60, 0.9, height_cm=163)
    assert result.weight_used == "actual"
    assert result.adjusted_bw_kg is None
    assert result.crcl_actual is not None


def test_batch_csv_continues_after_invalid_rows():
    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "in.csv")
        out = os.path.join(tmp, "out.csv")
        with open(inp, "w", newline="", encoding="utf-8") as handle:
            handle.write("patient_id,age,sex,weight_kg,weight_unit,creatinine,creatinine_unit,height_cm\n")
            handle.write("A1,50,M,70,kg,1.0,mg/dL,175\n")
            handle.write("A2,65,F,55,stone,1.2,mg/dL,160\n")
            handle.write("A3,55,M,75,kg,1.1,mg/dL,not-a-number\n")
            handle.write("A4,60,F,154,lbs,88.4,umol/L,165\n")

        results = cg.process_csv(inp, out)
        assert len(results) == 4
        assert results[0].crcl_actual is not None
        assert results[1].crcl_actual is None
        assert "Unsupported weight unit" in results[1].warnings[0]
        assert results[2].crcl_actual is None
        assert "could not convert string to float" in results[2].warnings[0]
        assert results[3].crcl_actual is not None
        assert math.isclose(results[3].weight_kg, 69.853, abs_tol=0.05)

        with open(out, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 4
        assert rows[1]["crcl_actual"] == ""


def test_batch_missing_required_column():
    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "in.csv")
        out = os.path.join(tmp, "out.csv")
        with open(inp, "w", encoding="utf-8") as handle:
            handle.write("patient_id,age,sex,weight_kg\nA1,50,M,70\n")
        with pytest.raises(ValueError, match="missing required columns"):
            cg.process_csv(inp, out)


def test_cli_single_and_batch():
    assert cg.main(["single", "--age", "50", "--sex", "M", "--weight", "70", "--creatinine", "1.0"]) == 0
    assert cg.main(["single", "--age", "50", "--sex", "F", "--weight", "154", "--weight-unit", "lbs", "--creatinine", "88.4", "--creatinine-unit", "umol/L"]) == 0
    assert cg.main(["single", "--age", "17", "--sex", "M", "--weight", "70", "--creatinine", "1.0"]) == 2

    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "in.csv")
        out = os.path.join(tmp, "out.csv")
        with open(inp, "w", encoding="utf-8") as handle:
            handle.write("patient_id,age,sex,weight_kg,weight_unit,creatinine,creatinine_unit,height_cm\n")
            handle.write("T1,50,M,70,kg,1.0,mg/dL,175\n")
        assert cg.main(["batch", "-i", inp, "-o", out]) == 0
        assert os.path.exists(out)
