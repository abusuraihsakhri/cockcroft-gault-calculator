"""Tests for cockcroft.py -- plain assert statements, stdlib only.

Run with: python test_cockcroft.py
"""

import csv
import math
import os
import tempfile

import cockcroft as cg


# ---------------------------------------------------------------------------
# Cockcroft-Gault equation
# ---------------------------------------------------------------------------

def test_cg_male_basic():
    """Standard male: 50yo, 70kg, Scr=1.0 -> CrCl = (90*70)/(72*1) = 87.5"""
    result = cg.cockcroft_gault(age=50, weight_kg=70, scr_mgdl=1.0, sex="M")
    expected = ((140 - 50) * 70) / (72 * 1.0)
    assert math.isclose(result, expected, abs_tol=0.01), (result, expected)


def test_cg_female_basic():
    """Standard female: 50yo, 60kg, Scr=1.0 -> CrCl = (90*60)/(72*1) * 0.85"""
    result = cg.cockcroft_gault(age=50, weight_kg=60, scr_mgdl=1.0, sex="F")
    expected = ((140 - 50) * 60) / (72 * 1.0) * 0.85
    assert math.isclose(result, expected, abs_tol=0.01), (result, expected)


def test_cg_female_85_factor():
    """Female CrCl should be 85% of male CrCl for same inputs."""
    male = cg.cockcroft_gault(age=60, weight_kg=80, scr_mgdl=1.2, sex="M")
    female = cg.cockcroft_gault(age=60, weight_kg=80, scr_mgdl=1.2, sex="F")
    assert math.isclose(female, male * 0.85, abs_tol=0.01), (male, female)


def test_cg_high_creatinine():
    """High creatinine should produce low CrCl."""
    result = cg.cockcroft_gault(age=70, weight_kg=70, scr_mgdl=4.0, sex="M")
    assert result < 20, result


def test_cg_young_healthy():
    """Young patient with normal creatinine should have high CrCl."""
    result = cg.cockcroft_gault(age=25, weight_kg=75, scr_mgdl=0.9, sex="M")
    assert result > 100, result


def test_cg_invalid_sex():
    try:
        cg.cockcroft_gault(age=50, weight_kg=70, scr_mgdl=1.0, sex="X")
        assert False, "expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# IBW formulas
# ---------------------------------------------------------------------------

def test_ibw_devine_male():
    """Devine male: 50 + 2.3*(70-60) = 50 + 23 = 73 kg for 5'10\" (70 inches)."""
    result = cg.ibw_devine(70, "M")
    assert math.isclose(result, 73.0, abs_tol=0.01), result


def test_ibw_devine_female():
    """Devine female: 45.5 + 2.3*(64-60) = 45.5 + 9.2 = 54.7 kg for 5'4\"."""
    result = cg.ibw_devine(64, "F")
    assert math.isclose(result, 54.7, abs_tol=0.01), result


def test_ibw_robinson_male():
    """Robinson male: 52 + 1.9*(70-60) = 52 + 19 = 71 kg."""
    result = cg.ibw_robinson(70, "M")
    assert math.isclose(result, 71.0, abs_tol=0.01), result


def test_ibw_robinson_female():
    """Robinson female: 49 + 1.7*(64-60) = 49 + 6.8 = 55.8 kg."""
    result = cg.ibw_robinson(64, "F")
    assert math.isclose(result, 55.8, abs_tol=0.01), result


def test_ibw_miller_male():
    """Miller male: 56.2 + 1.41*(70-60) = 56.2 + 14.1 = 70.3 kg."""
    result = cg.ibw_miller(70, "M")
    assert math.isclose(result, 70.3, abs_tol=0.01), result


def test_ibw_miller_female():
    """Miller female: 53.1 + 1.36*(64-60) = 53.1 + 5.44 = 58.54 kg."""
    result = cg.ibw_miller(64, "F")
    assert math.isclose(result, 58.54, abs_tol=0.01), result


def test_ibw_hamwi_male():
    """Hamwi male: 48 + 2.7*(70-60) = 48 + 27 = 75 kg."""
    result = cg.ibw_hamwi(70, "M")
    assert math.isclose(result, 75.0, abs_tol=0.01), result


def test_ibw_hamwi_female():
    """Hamwi female: 45.5 + 2.2*(64-60) = 45.5 + 8.8 = 54.3 kg."""
    result = cg.ibw_hamwi(64, "F")
    assert math.isclose(result, 54.3, abs_tol=0.01), result


# ---------------------------------------------------------------------------
# Adjusted Body Weight
# ---------------------------------------------------------------------------

def test_adjusted_body_weight():
    """AjBW = IBW + 0.4 * (actual - IBW)."""
    ibw = 70.0
    actual = 100.0
    result = cg.adjusted_body_weight(actual, ibw)
    expected = 70 + 0.4 * (100 - 70)
    assert math.isclose(result, expected, abs_tol=0.01), (result, expected)


def test_adjusted_body_weight_no_adjustment_needed():
    """When actual == IBW, adjusted equals IBW."""
    ibw = 65.0
    result = cg.adjusted_body_weight(65.0, ibw)
    assert math.isclose(result, 65.0, abs_tol=0.01), result


def test_percent_ibw():
    """100kg actual / 70kg IBW = 142.9%."""
    result = cg.percent_ibw(100, 70)
    assert math.isclose(result, 142.86, abs_tol=0.1), result


# ---------------------------------------------------------------------------
# Height/weight conversion
# ---------------------------------------------------------------------------

def test_height_to_inches():
    """177.8 cm = 70 inches."""
    result = cg.height_to_inches(177.8)
    assert math.isclose(result, 70.0, abs_tol=0.1), result


def test_weight_to_kg():
    """154 lbs ≈ 69.85 kg."""
    result = cg.weight_to_kg(154)
    assert math.isclose(result, 69.85, abs_tol=0.1), result


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------

def test_creatinine_conversion():
    """1.0 mg/dL = 88.4 umol/L."""
    result = cg.creatinine_to_mgdl(88.4, "umol/L")
    assert math.isclose(result, 1.0, abs_tol=0.01), result


def test_creatinine_unsupported_unit():
    try:
        cg.creatinine_to_mgdl(1.0, "mg/L")
        assert False, "expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Renal dosing categories
# ---------------------------------------------------------------------------

def test_dosing_normal():
    cat, _ = cg.renal_dosing_category(100)
    assert cat == "Normal renal function"


def test_dosing_mild():
    cat, _ = cg.renal_dosing_category(70)
    assert cat == "Mild impairment"


def test_dosing_moderate():
    cat, _ = cg.renal_dosing_category(45)
    assert cat == "Moderate impairment"


def test_dosing_severe():
    cat, _ = cg.renal_dosing_category(20)
    assert cat == "Severe impairment"


def test_dosing_kidney_failure():
    cat, _ = cg.renal_dosing_category(10)
    assert cat == "Kidney failure"


# ---------------------------------------------------------------------------
# Patient workflow
# ---------------------------------------------------------------------------

def test_calculate_patient_no_height():
    result = cg.calculate_patient("P1", 50, "M", 70, 1.0)
    assert result.crcl_actual is not None
    assert result.ibw_kg is None
    assert result.dosing_category is not None


def test_calculate_patient_with_height_obese():
    """Patient >130% IBW should get adjusted BW CrCl."""
    result = cg.calculate_patient("P2", 50, "M", 120, 1.0, height_cm=170)
    assert result.ibw_kg is not None
    assert result.percent_ibw > 130
    assert result.adjusted_bw_kg is not None
    assert result.crcl_adjusted is not None
    assert result.weight_used == "adjusted"


def test_calculate_patient_with_height_normal():
    """Patient at normal weight should not use adjusted BW."""
    result = cg.calculate_patient("P3", 40, "F", 60, 0.9, height_cm=163)
    assert result.ibw_kg is not None
    assert result.percent_ibw <= 130
    assert result.adjusted_bw_kg is None
    assert result.weight_used == "actual"


# ---------------------------------------------------------------------------
# CSV batch processing
# ---------------------------------------------------------------------------

def test_batch_csv():
    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "in.csv")
        out = os.path.join(tmp, "out.csv")
        with open(inp, "w", newline="") as f:
            f.write("patient_id,age,sex,weight_kg,weight_unit,creatinine,creatinine_unit,height_cm\n")
            f.write("A1,50,M,70,kg,1.0,mg/dL,175\n")
            f.write("A2,65,F,55,kg,1.2,mg/dL,\n")
        results = cg.process_csv(inp, out)
        assert len(results) == 2
        assert results[0].crcl_actual is not None
        assert results[1].crcl_actual is not None
        assert os.path.exists(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_single():
    rc = cg.main(["single", "--age", "50", "--sex", "M", "--weight", "70", "--creatinine", "1.0"])
    assert rc == 0


def test_cli_single_with_height():
    rc = cg.main(["single", "--age", "50", "--sex", "F", "--weight", "80",
                   "--creatinine", "1.0", "--height-cm", "165"])
    assert rc == 0


def test_cli_batch():
    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "in.csv")
        out = os.path.join(tmp, "out.csv")
        with open(inp, "w", newline="") as f:
            f.write("patient_id,age,sex,weight_kg,weight_unit,creatinine,creatinine_unit,height_cm\n")
            f.write("T1,50,M,70,kg,1.0,mg/dL,175\n")
        rc = cg.main(["batch", "--input", inp, "--output", out])
        assert rc == 0
        assert os.path.exists(out)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all():
    tests = [obj for name, obj in globals().items() if name.startswith("test_") and callable(obj)]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS: {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {t.__name__} -- {e}")
    print(f"\n{passed}/{passed + failed} tests passed.")
    return failed


if __name__ == "__main__":
    import sys
    sys.exit(run_all())
