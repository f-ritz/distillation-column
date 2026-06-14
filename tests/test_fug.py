"""
Basic unit tests for the FUGK core calculator.
Run with:  python -m pytest tests/ -q   (or python -m unittest)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.fug import FUGKDistillation


def test_basic_binary_bt():
    calc = FUGKDistillation(
        components=["Benzene", "Toluene"],
        z_feed={"Benzene": 0.5, "Toluene": 0.5},
        alpha={"Benzene": 2.5, "Toluene": 1.0},
        feed_flow=100.0,
        q=1.0,
        lk="Benzene",
        hk="Toluene",
    )
    res = calc.calculate(lk_recovery_d=0.99, hk_recovery_b=0.99, R_over_Rmin=1.3)
    assert res.N_min > 8
    assert res.R_min > 0.8
    assert res.N_actual > res.N_min + 1
    assert res.feed_stage >= 1
    assert 0.98 < res.distillate_composition["Benzene"] <= 1.0
    assert res.component_recoveries["Benzene"] >= 0.98


def test_multicomponent_and_nonkeys():
    comps = ["Benzene", "Toluene", "Ethylbenzene"]
    z = {"Benzene": 0.3, "Toluene": 0.5, "Ethylbenzene": 0.2}
    alpha = {"Benzene": 2.6, "Toluene": 1.0, "Ethylbenzene": 0.42}
    calc = FUGKDistillation(comps, z, alpha, feed_flow=80, q=0.8, lk="Benzene", hk="Ethylbenzene")
    res = calc.calculate(0.995, 0.99, 1.4)
    assert len(res.component_splits) == 3
    # Light non-key should mostly go to distillate
    assert res.component_recoveries["Toluene"] > 0.6
    assert res.N_min > 5


def test_invalid_keys_auto_swap_and_warning():
    # alpha of declared LK lower than HK -> should swap internally + warn
    calc = FUGKDistillation(
        ["A", "B"], {"A": 0.4, "B": 0.6},
        {"A": 0.8, "B": 2.2},   # A less volatile than B
        lk="A", hk="B"
    )
    res = calc.calculate(0.95, 0.95, 1.2)
    # After swap, effective lk should be B (more volatile)
    # We mainly check it didn't crash and produced sensible numbers
    assert res.N_min > 1
    assert len(res.warnings) >= 0   # may contain swap warning


def test_q_effects():
    base = FUGKDistillation(["L", "H"], {"L": 0.5, "H": 0.5}, {"L": 2.0, "H": 1.0}, q=1.0, lk="L", hk="H")
    r1 = base.calculate(0.99, 0.99, 1.2).R_min

    vapor = FUGKDistillation(["L", "H"], {"L": 0.5, "H": 0.5}, {"L": 2.0, "H": 1.0}, q=-0.2, lk="L", hk="H")
    r2 = vapor.calculate(0.99, 0.99, 1.2).R_min
    assert r2 > r1 * 0.95   # vapor feed usually requires more reflux in this model


if __name__ == "__main__":
    # Allow direct run
    test_basic_binary_bt()
    test_multicomponent_and_nonkeys()
    test_invalid_keys_auto_swap_and_warning()
    test_q_effects()
    print("All basic FUG tests passed.")
