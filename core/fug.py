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
    feed_stage_min: int   # feed location if operating at total reflux (N_min)
    feed_stage_actual: int  # feed location at the actual (operating) number of stages
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

        # Validate keys exist
        if self.lk not in self.components:
            self.lk = self.components[0]
        if self.hk not in self.components:
            self.hk = self.components[-1]

        # Ensure alpha_LK > alpha_HK (convention: higher alpha = more volatile)
        a_lk = self.alpha.get(self.lk, 1.0)
        a_hk = self.alpha.get(self.hk, 1.0)
        if a_lk < a_hk:
            self.warnings.append(f"alpha of LK ({self.lk}) < alpha of HK ({self.hk}). Swapping keys for calculation.")
            self.lk, self.hk = self.hk, self.lk

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

        # Fenske - Minimum stages (keys only)
        alpha_lk_hk = self.alpha[self.lk] / self.alpha[self.hk]
        if alpha_lk_hk <= 1.0:
            self.warnings.append("Relative volatility of LK/HK <= 1 — separation impossible or keys reversed.")
            alpha_lk_hk = 1.05
        N_min = np.log((x_lk_d / max(x_lk_b, 1e-8)) * (x_hk_b / max(x_hk_d, 1e-8))) / np.log(alpha_lk_hk)
        N_min = max(N_min, 1.0)

        # Kirkbride feed stage at minimum stages (total reflux case)
        feed_stage_min = self._kirkbride(N_min, x_lk_d, x_lk_b, x_hk_d, x_hk_b)

        # Component distributions using Fenske for non-keys (used for both final results and Underwood approx)
        component_recoveries = {}
        component_splits = {}

        for comp in self.components:
            if comp == self.lk:
                rec_d = lk_recovery_d
            elif comp == self.hk:
                rec_d = 1 - hk_recovery_b
            else:
                # Fenske-style distribution for non-keys at total reflux N_min
                alpha_comp = self.alpha[comp] / self.alpha[self.hk]
                rec_d = (alpha_comp ** N_min) / (1 + (alpha_comp ** N_min))
                rec_d = float(np.clip(rec_d, 0.001, 0.999))

            component_recoveries[comp] = rec_d
            d_flow = rec_d * self.z_feed[comp] * self.feed_flow
            b_flow = (1 - rec_d) * self.z_feed[comp] * self.feed_flow
            component_splits[comp] = (d_flow, b_flow)

        # Approximate distillate mole fractions from the Fenske splits (needed for Underwood)
        total_d_approx = sum(s[0] for s in component_splits.values())
        xd_approx = {c: component_splits[c][0] / max(total_d_approx, 1e-6) for c in self.components}

        # Proper multicomponent Underwood minimum reflux
        R_min = self._underwood_rmin(xd_approx)

        # Operating conditions
        R_actual = R_min * R_over_Rmin

        # Gilliland correlation
        N_actual = self._gilliland(R_actual, R_min, N_min)
        N_actual = min(N_actual, max_stages)

        # Recompute key x using final splits for accuracy
        d_lk_final, b_lk_final = component_splits[self.lk]
        d_hk_final, b_hk_final = component_splits[self.hk]
        total_d_final = sum(s[0] for s in component_splits.values())
        total_b_final = sum(s[1] for s in component_splits.values())
        x_lk_d = d_lk_final / max(total_d_final, 1e-6)
        x_hk_d = d_hk_final / max(total_d_final, 1e-6)
        x_lk_b = b_lk_final / max(total_b_final, 1e-6)
        x_hk_b = b_hk_final / max(total_b_final, 1e-6)

        # Kirkbride feed stage at actual operating stages
        feed_stage_actual = self._kirkbride(N_actual, x_lk_d, x_lk_b, x_hk_d, x_hk_b)

        # Build results
        total_d = sum(s[0] for s in component_splits.values())
        total_b = sum(s[1] for s in component_splits.values())

        results = DistillationResults(
            N_min=round(N_min, 2),
            R_min=round(R_min, 3),
            N_actual=round(N_actual, 1),
            R_actual=round(R_actual, 3),
            feed_stage_min=feed_stage_min,
            feed_stage_actual=feed_stage_actual,
            distillate_composition={c: round(component_splits[c][0] / max(total_d, 1e-6), 4) for c in self.components},
            bottoms_composition={c: round(component_splits[c][1] / max(total_b, 1e-6), 4) for c in self.components},
            component_recoveries=component_recoveries,
            component_splits=component_splits,
            warnings=self.warnings
        )
        return results

    def _underwood_rmin(self, xd: Dict[str, float]) -> float:
        """
        Proper Underwood minimum reflux for (pseudo) binary or multicomponent constant-alpha.
        1. Numerically solve for theta from the feed Underwood equation:
              sum( alpha_i * z_i / (alpha_i - theta) ) = 1 - q
           theta lies between alpha_hk and alpha_lk (assuming alpha_lk > alpha_hk > 0).
        2. Then:
              R_min = sum( alpha_i * xD_i / (alpha_i - theta) ) - 1
        """
        alpha_lk = self.alpha[self.lk]
        alpha_hk = self.alpha[self.hk]
        if alpha_lk <= alpha_hk:
            alpha_lk = alpha_hk + 0.2

        # Feasible bracket for the relevant root
        lo = min(alpha_hk, alpha_lk) + 1e-6
        hi = max(alpha_hk, alpha_lk) - 1e-6
        if lo >= hi:
            lo, hi = 0.5, alpha_lk + 1.0   # very wide fallback

        # Try to tighten bracket around a sign change
        def f(theta):
            s = 0.0
            for c in self.components:
                a = self.alpha.get(c, 1.0)
                z = self.z_feed.get(c, 0.0)
                den = a - theta
                if abs(den) < 1e-9:
                    den = 1e-9 if den >= 0 else -1e-9
                s += (a * z) / den
            return s - (1.0 - self.q)

        # Bisection search
        f_lo = f(lo)
        f_hi = f(hi)
        # If same sign, expand the interval
        for _ in range(8):
            if f_lo * f_hi <= 0:
                break
            lo = max(1e-4, lo * 0.6)
            hi = hi * 1.4
            f_lo = f(lo)
            f_hi = f(hi)

        theta = None
        for _ in range(60):
            mid = (lo + hi) / 2.0
            fm = f(mid)
            if abs(fm) < 1e-8:
                theta = mid
                break
            if f_lo * fm <= 0:
                hi = mid
                f_hi = fm
            else:
                lo = mid
                f_lo = fm
        if theta is None:
            theta = (lo + hi) / 2.0
            self.warnings.append("Underwood theta root did not fully converge — using approximate value.")

        # Now compute Rmin from distillate composition
        rmin_sum = 0.0
        for c in self.components:
            a = self.alpha.get(c, 1.0)
            xdi = xd.get(c, 0.0)
            den = a - theta
            if abs(den) < 1e-9:
                den = 1e-9 if den >= 0 else -1e-9
            rmin_sum += (a * xdi) / den

        R_min = rmin_sum - 1.0

        # Apply simple q correction / bounds (empirical guard)
        if self.q > 1.0:   # subcooled feed tends to lower Rmin slightly
            R_min *= 0.92
        elif self.q < 0.0:  # superheated vapor feed
            R_min *= 1.08

        # Practical floor for most real columns (prevents nonsensical 0.01 values on very easy splits)
        R_min = max(R_min, 0.15)
        return R_min

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
    print(f"Feed stage (min) = {results.feed_stage_min}")
    print(f"Feed stage (actual) = {results.feed_stage_actual}")