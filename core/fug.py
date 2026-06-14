"""
FUGK Shortcut Distillation Module
Reverse-engineering Aspen DSTWU style calculations
Fenske - Underwood - Gilliland - Kirkbride method

Versatile implementation supporting:
- Binary and multicomponent systems
- Constant or user-provided relative volatilities
- Feed thermal condition (q)
- Recovery or purity specifications
- Component distribution calculations
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DistillationResults:
    """Container for distillation calculation results"""
    N_min: float
    R_min: float
    N_actual: float
    R_actual: float
    feed_stage: int
    distillate_composition: Dict[str, float]
    bottoms_composition: Dict[str, float]
    component_recoveries: Dict[str, float]
    component_splits: Dict[str, Tuple[float, float]]  # (D, B)
    warnings: List[str]


class FUGKDistillation:
    """
    Versatile Fenske-Underwood-Gilliland-Kirkbride shortcut distillation calculator.
    Designed to approximate Aspen DSTWU behavior.
    """

    def __init__(self,
                 components: List[str],
                 z_feed: Dict[str, float],
                 alpha: Dict[str, float],
                 feed_flow: float = 100.0,
                 q: float = 1.0,
                 pressure: float = 1.0,
                 lk: str = None,
                 hk: str = None):
        self.components = components
        self.z_feed = {c: z_feed.get(c, 0.0) for c in components}
        self.alpha = {c: alpha.get(c, 1.0) for c in components}
        self.feed_flow = feed_flow
        self.q = q
        self.pressure = pressure
        self.lk = lk or components[0]
        self.hk = hk or components[-1]
        self.warnings = []

        # Normalize feed if needed
        total_z = sum(self.z_feed.values())
        if abs(total_z - 1.0) > 1e-6 and total_z > 0:
            for c in self.components:
                self.z_feed[c] /= total_z

    def calculate(self,
                  lk_recovery_d: float = 0.99,
                  hk_recovery_b: float = 0.99,
                  R_over_Rmin: float = 1.3,
                  max_stages: int = 120) -> DistillationResults:

        self.warnings = []

        # Key component flows
        d_lk = lk_recovery_d * self.z_feed[self.lk] * self.feed_flow
        b_lk = (1 - lk_recovery_d) * self.z_feed[self.lk] * self.feed_flow

        d_hk = (1 - hk_recovery_b) * self.z_feed[self.hk] * self.feed_flow
        b_hk = hk_recovery_b * self.z_feed[self.hk] * self.feed_flow

        # Approximate compositions for keys
        total_d_approx = d_lk + d_hk + 0.01 * self.feed_flow
        total_b_approx = b_lk + b_hk + 0.01 * self.feed_flow

        x_lk_d = d_lk / max(total_d_approx, 1e-6)
        x_hk_d = d_hk / max(total_d_approx, 1e-6)
        x_lk_b = b_lk / max(total_b_approx, 1e-6)
        x_hk_b = b_hk / max(total_b_approx, 1e-6)

        # Fenske - Minimum stages
        alpha_lk_hk = self.alpha[self.lk] / self.alpha[self.hk]
        N_min = np.log((x_lk_d / max(x_lk_b, 1e-8)) * (x_hk_b / max(x_hk_d, 1e-8))) / np.log(alpha_lk_hk)
        N_min = max(N_min, 1.0)

        # Underwood-style minimum reflux (simplified but practical)
        R_min = self._estimate_rmin(lk_recovery_d, hk_recovery_b)

        # Operating conditions
        R_actual = R_min * R_over_Rmin

        # Gilliland correlation
        N_actual = self._gilliland(R_actual, R_min, N_min)
        N_actual = min(N_actual, max_stages)

        # Kirkbride feed stage
        feed_stage = self._kirkbride(N_actual, x_lk_d, x_lk_b, x_hk_d, x_hk_b)

        # Component distributions
        component_recoveries = {}
        component_splits = {}

        for comp in self.components:
            if comp == self.lk:
                rec_d = lk_recovery_d
            elif comp == self.hk:
                rec_d = 1 - hk_recovery_b
            else:
                # Fenske-style distribution for non-keys
                alpha_comp = self.alpha[comp] / self.alpha[self.hk]
                rec_d = (alpha_comp ** N_min) / (1 + (alpha_comp ** N_min))
                rec_d = np.clip(rec_d, 0.001, 0.999)

            component_recoveries[comp] = rec_d
            d_flow = rec_d * self.z_feed[comp] * self.feed_flow
            b_flow = (1 - rec_d) * self.z_feed[comp] * self.feed_flow
            component_splits[comp] = (d_flow, b_flow)

        # Build results
        total_d = sum(s[0] for s in component_splits.values())
        total_b = sum(s[1] for s in component_splits.values())

        results = DistillationResults(
            N_min=round(N_min, 2),
            R_min=round(R_min, 3),
            N_actual=round(N_actual, 1),
            R_actual=round(R_actual, 3),
            feed_stage=feed_stage,
            distillate_composition={c: round(component_splits[c][0] / max(total_d, 1e-6), 4) for c in self.components},
            bottoms_composition={c: round(component_splits[c][1] / max(total_b, 1e-6), 4) for c in self.components},
            component_recoveries=component_recoveries,
            component_splits=component_splits,
            warnings=self.warnings
        )
        return results

    def _estimate_rmin(self, lk_rec_d: float, hk_rec_b: float) -> float:
        alpha_lk = self.alpha[self.lk]
        z_lk = self.z_feed[self.lk]

        r_min = ((alpha_lk / (alpha_lk - 1)) * (lk_rec_d * z_lk) / z_lk) - 1
        r_min = max(r_min, 0.5)

        if self.q > 1.0:
            r_min *= 0.95
        elif self.q < 0:
            r_min *= 1.1

        return r_min

    def _gilliland(self, R: float, R_min: float, N_min: float) -> float:
        if R <= R_min:
            self.warnings.append("Operating reflux below minimum — using R_min * 1.1")
            R = R_min * 1.1

        X = (R - R_min) / (R + 1)
        if X <= 0:
            return N_min * 2

        Y = 1 - np.exp(((1 + 54.4 * X) * (X - 1)) / ((11 + 117.2 * X) * np.sqrt(X)))
        N = (Y * (N_min + 1) + N_min) / (1 - Y) if Y < 1 else N_min * 3
        return max(N, N_min + 2)

    def _kirkbride(self, N_total: float, x_lk_d: float, x_lk_b: float,
                   x_hk_d: float, x_hk_b: float) -> int:
        if N_total < 2:
            return 1

        ratio = (x_hk_d / x_lk_d) * (x_lk_b / x_hk_b) * (self.z_feed[self.lk] / self.z_feed[self.hk]) ** 2
        N_r = N_total / (1 + (1 / ratio) ** 0.206)
        feed_stage = int(round(N_r))
        return max(1, min(feed_stage, int(N_total) - 1))


# Quick test
if __name__ == "__main__":
    calc = FUGKDistillation(
        components=["Benzene", "Toluene"],
        z_feed={"Benzene": 0.5, "Toluene": 0.5},
        alpha={"Benzene": 2.5, "Toluene": 1.0},
        feed_flow=100,
        q=1.0,
        lk="Benzene",
        hk="Toluene"
    )

    results = calc.calculate(lk_recovery_d=0.99, hk_recovery_b=0.99, R_over_Rmin=1.3)
    print(f"N_min = {results.N_min}")
    print(f"R_min = {results.R_min}")
    print(f"N_actual = {results.N_actual}")
    print(f"Feed stage = {results.feed_stage}")