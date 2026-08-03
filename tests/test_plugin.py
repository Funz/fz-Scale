#!/usr/bin/env python3
"""
Basic test suite for fz-scale plugin.

These tests verify the plugin structure without requiring SCALE to be installed.
They test:
- Model file validity
- Variable parsing
- Input file compilation
- Calculator configuration
- Output parsing (python:// expressions) on a real KENO output sample

The KENO output sample in tests/fixtures/Scale-keno/godiva.out is a genuine
SCALE/KENO-V.a result excerpt (csas5_example.out from idaholab/raven's
CodeInterfaceTests, https://github.com/idaholab/raven), used here only to
validate that the Scale-keno model's "python://" output expressions parse a
real "final results table" correctly, on any OS (no bash/grep/awk required).
"""

import os
import json
import math
import shutil
import tempfile
import sys


def test_model_files():
    """Test that all model JSON files are valid and have required fields."""
    print("Testing model files...")
    
    models = [
        ".fz/models/Scale-keno.json",
        ".fz/models/Scale-tsunami.json",
        ".fz/models/Scale-xsdrnpm.json",
        ".fz/models/Scale-shift.json"
    ]
    
    required_fields = ["id", "varprefix", "commentline", "output"]
    
    for model_file in models:
        print(f"  Checking {model_file}...", end=" ")
        
        # Check file exists
        assert os.path.exists(model_file), f"File not found: {model_file}"
        
        # Load and validate JSON
        with open(model_file, 'r') as f:
            model = json.load(f)
        
        # Check required fields
        for field in required_fields:
            assert field in model, f"Missing field '{field}' in {model_file}"

        # Delimiters: either a single shared 'delim', or the separate
        # 'var_delim' (for variables) / 'formula_delim' (for formulas)
        assert "delim" in model or "var_delim" in model or "formula_delim" in model, (
            f"Missing delimiter field ('delim', 'var_delim' or 'formula_delim') in {model_file}"
        )
        
        # Check output section has at least one variable
        assert len(model["output"]) > 0, f"No output variables in {model_file}"
        
        print("✓")
    
    print("  All model files valid!\n")


def test_calculator_files():
    """Test that calculator JSON files are valid."""
    print("Testing calculator configuration files...")

    calculators = [
        ".fz/calculators/localhost_Scale.json"
    ]
    
    for calc_file in calculators:
        print(f"  Checking {calc_file}...", end=" ")
        
        # Check file exists
        assert os.path.exists(calc_file), f"File not found: {calc_file}"
        
        # Load and validate JSON
        with open(calc_file, 'r') as f:
            calc = json.load(f)
        
        # Check required fields
        assert "uri" in calc, f"Missing 'uri' field in {calc_file}"
        assert "models" in calc, f"Missing 'models' field in {calc_file}"
        
        print("✓")
    
    print("  All calculator files valid!\n")


def test_calculator_scripts():
    """Test that calculator shell scripts exist and are executable."""
    print("Testing calculator shell scripts...")
    
    scripts = [
        ".fz/calculators/Scale-keno.sh",
        ".fz/calculators/Scale-tsunami.sh",
        ".fz/calculators/Scale-xsdrnpm.sh",
        ".fz/calculators/Scale-shift.sh"
    ]
    
    for script_file in scripts:
        print(f"  Checking {script_file}...", end=" ")
        
        # Check file exists
        assert os.path.exists(script_file), f"File not found: {script_file}"
        
        # Check if executable
        assert os.access(script_file, os.X_OK), f"Script not executable: {script_file}"
        
        print("✓")
    
    print("  All calculator scripts valid!\n")


def test_example_files():
    """Test that example files exist."""
    print("Testing example files...")
    
    examples = [
        "examples/Scale-keno/godiva.inp",
        "examples/Scale-shift/godiva.inp",
    ]
    
    for example_file in examples:
        print(f"  Checking {example_file}...", end=" ")
        assert os.path.exists(example_file), f"File not found: {example_file}"
        print("✓")
    
    print("  All example files present!\n")


def test_keno_output_parsing():
    """Test that the Scale-keno model's python:// output expressions
    correctly parse a real KENO "final results table" (see module docstring
    for the fixture's origin)."""
    print("Testing Scale-keno output parsing...")

    try:
        import fz
    except ImportError:
        print("  fz module not installed - skipping output parsing test")
        print("  (Install with: pip install git+https://github.com/Funz/fz.git)\n")
        return

    expected = {
        "mean_keff": 0.952,
        "sigma_keff": 0.020,
        "mean_E_lethargy": 0.280003,
        "sigma_E_lethargy": 0.00358169,
        "mean_free_path": 1.23628,
        "sigma_free_path": 0.00823879,
        "mean_nubar": 2.44645,
        "sigma_nubar": 0.000111459,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(
            os.path.join("tests", "fixtures", "Scale-keno", "godiva.out"),
            os.path.join(tmpdir, "godiva.out"),
        )
        print("  Running fz.fzo() on sample output...", end=" ")
        result = fz.fzo(tmpdir, "Scale-keno")
        row = result.iloc[0]
        for key, value in expected.items():
            assert key in row, f"Missing output '{key}' in parsed result"
            assert math.isclose(row[key], value, rel_tol=1e-6), (
                f"Output '{key}': expected {value}, got {row[key]}"
            )
        print("✓")

    print("  Scale-keno output parsing test passed!\n")


def test_dual_delimiters():
    """Test that the plugin supports two distinct delimiters at once:
    "()" for variables (varprefix "&") and "{}" for formulas (formulaprefix
    "@"), as configured via the model's "var_delim"/"formula_delim" fields."""
    print("Testing dual delimiters (variables '()' / formulas '{}')...")

    try:
        import fz
    except ImportError:
        print("  fz module not installed - skipping dual delimiter test")
        print("  (Install with: pip install git+https://github.com/Funz/fz.git)\n")
        return

    content = (
        "'test\n"
        " sphere 10    &(r)\n"
        " diameter     @{2*r}\n"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        inp = os.path.join(tmpdir, "test.inp")
        with open(inp, "w") as f:
            f.write(content)

        print("  Testing fz.fzi() picks up variable 'r'...", end=" ")
        variables = fz.fzi(inp, "Scale-keno")
        assert "r" in variables, "Variable 'r' (delimiter '()') not found"
        print("✓")

        print("  Testing fz.fzc() substitutes '()' and evaluates '{}'...", end=" ")
        with tempfile.TemporaryDirectory() as outdir:
            fz.fzc(inp, {"r": 5.0}, "Scale-keno", output_dir=outdir)
            compiled = os.path.join(outdir, "r=5.0", "test.inp")
            assert os.path.exists(compiled), "Compiled file not created"
            with open(compiled) as f:
                out_content = f.read()
                assert "5.0" in out_content, "Variable '&(r)' not substituted"
                assert "&(r)" not in out_content, "Variable marker still present"
                assert "10.0" in out_content, "Formula '@{2*r}' not evaluated"
                assert "@{2*r}" not in out_content, "Formula marker still present"
        print("✓")

    print("  Dual delimiter test passed!\n")


def test_with_fz():
    """Test integration with fz framework (if available)."""
    print("Testing fz framework integration...")
    
    try:
        import fz
        print("  fz module found ✓")
        
        # Test parsing input file
        print("  Testing fz.fzi() on godiva.inp...", end=" ")
        variables = fz.fzi("examples/Scale-keno/godiva.inp", "Scale-keno")
        assert "r" in variables, "Variable 'r' not found in parsed input"
        print("✓")
        
        # Test compiling input file
        print("  Testing fz.fzc() compilation...", end=" ")
        with tempfile.TemporaryDirectory() as tmpdir:
            fz.fzc(
                "examples/Scale-keno/godiva.inp",
                {"r": 8.741},
                "Scale-keno",
                output_dir=tmpdir
            )
            
            # Check compiled file exists
            compiled_file = os.path.join(tmpdir, "r=8.741" ,"godiva.inp")
            assert os.path.exists(compiled_file), "Compiled file not created"
            
            # Check variable was substituted
            with open(compiled_file, 'r') as f:
                content = f.read()
                assert "8.741" in content, "Variable not substituted"
                assert "&(r)" not in content, "Variable marker still present"
        print("✓")
        
        print("  fz integration tests passed!\n")
        
    except ImportError:
        print("  fz module not installed - skipping integration tests")
        print("  (Install with: pip install git+https://github.com/Funz/fz.git)\n")


def main():
    """Run all tests."""
    print("=" * 70)
    print("fz-scale Plugin Test Suite")
    print("=" * 70)
    print()
    
    # Change to repository root if needed
    if not os.path.exists(".fz"):
        if os.path.exists("../fz-scale/.fz"):
            os.chdir("../fz-scale")
        else:
            print("Error: Could not find .fz directory")
            print("Please run this script from the fz-scale repository root")
            return 1
    
    try:
        test_model_files()
        test_calculator_files()
        test_calculator_scripts()
        test_example_files()
        test_keno_output_parsing()
        test_dual_delimiters()
        test_with_fz()
        
        print("=" * 70)
        print("All tests passed! ✓")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
