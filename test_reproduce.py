"""Run analysis.py in a temporary directory and check that it rebuilds the
committed results.json byte for byte, and that the frontier numbers all come
from the computed frontier reliability."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


class ReproduceTest(unittest.TestCase):
    def test_results_regenerate_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable, os.path.join(HERE, "analysis.py")],
                           cwd=tmp, check=True, stdout=subprocess.DEVNULL)
            with open(os.path.join(tmp, "results.json"), "rb") as f:
                fresh = f.read()
        with open(os.path.join(HERE, "results.json"), "rb") as f:
            committed = f.read()
        self.assertEqual(fresh, committed, "results.json no longer matches what analysis.py produces")

    def test_frontier_numbers_use_the_computed_reliability(self):
        with open(os.path.join(HERE, "results.json")) as f:
            d = json.load(f)
        rho = next(r["icc"] for r in d["reliability_estimates"] if r["label"].startswith("Frontier"))
        self.assertEqual(rho, round(25 / (25 + 1.25 ** 2), 3))
        self.assertAlmostEqual(d["gap_decomposition"]["benchmark_unreliability"], round(1 - rho, 4))
        self.assertAlmostEqual(d["gap_decomposition"]["ceiling"], round(rho * 0.75 * 0.25, 4))
        for e in d["attenuation_examples"]:
            self.assertAlmostEqual(e["r_corrected"], round(e["r_observed"] / (rho * 0.75) ** 0.5, 3))


if __name__ == "__main__":
    unittest.main()
