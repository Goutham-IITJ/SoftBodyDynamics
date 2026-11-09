"""Run all unit suites without regenerating prior-stage verification artifacts."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
suite=unittest.TestSuite()
for folder in ['analysis/material','analysis/fem','analysis/fem_solver','analysis/sponge','analysis/calibration','demo']:
    suite.addTests(unittest.TestLoader().discover(str(ROOT/folder),pattern='test_*.py'))
result=unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(not result.wasSuccessful())
