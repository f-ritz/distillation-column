"""
Chemical Database - PubChem Search + Local Caching
No hardcoded chemicals. Searches real database and caches results locally.
Supports PyInstaller frozen executables.
"""

import json
import os
import sys
from typing import List, Dict, Optional, Tuple
import pubchempy as pcp
import numpy as np


def _get_base_dir() -> str:
    """Get base directory for bundled data (works in dev and PyInstaller onefile)."""
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        return sys._MEIPASS
    return os.path.dirname(__file__)


def _get_writable_cache_path() -> str:
    """Return a writable location for the chemicals cache (user home to survive updates)."""
    try:
        cache_dir = os.path.join(os.path.expanduser("~"), ".fugk")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, "chemicals_cache.json")
    except Exception:
        # Fallback next to script (may be read-only in bundle)
        return os.path.join(_get_base_dir(), "chemicals_cache.json")


CACHE_FILE = os.path.join(_get_base_dir(), "chemicals_cache.json")
WRITABLE_CACHE_FILE = _get_writable_cache_path()


def _load_cache() -> dict:
    # Try writable user cache first, then bundled
    for path in (WRITABLE_CACHE_FILE, CACHE_FILE):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return {}


def _save_cache(cache: dict):
    target = WRITABLE_CACHE_FILE
    try:
        with open(target, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Cache save failed: {e}")


_cache = _load_cache()


def search_chemicals(query: str, limit: int = 15) -> List[Dict]:
    """
    Search chemicals using PubChem.
    - Primary search: by name (supports partial/substring matches via PubChem + local cache augmentation).
    - If the query looks like a CAS number (contains '-' or is numeric), we also search the 'cas' namespace.
    - Results include IUPAC name (preferred), formula, MW, and CAS when available.
    - The dropdown in the GUI shows rich info (name + formula + CAS) so you know exactly what is being added.
    - Local cache ensures previously discovered chemicals appear in substring searches even offline.
    """
    query = query.strip()
    if not query:
        return []

    q_lower = query.lower()

    # Get direct results for this query (cache or PubChem)
    direct_results = []
    if q_lower in _cache:
        direct_results = _cache[q_lower]
    else:
        try:
            compounds = []
            # Always try name search (good for partial names, IUPAC, common names, synonyms)
            compounds.extend(pcp.get_compounds(query, "name"))

            # If it looks like a CAS (dashes or mostly digits), also search CAS namespace explicitly
            looks_like_cas = '-' in query or (query.replace('-', '').isdigit() and len(query.replace('-', '')) >= 5)
            if looks_like_cas:
                try:
                    compounds.extend(pcp.get_compounds(query, "cas"))
                except Exception:
                    pass

            # Dedup by CID
            seen_cids = set()
            unique_compounds = []
            for comp in compounds:
                if comp.cid not in seen_cids:
                    seen_cids.add(comp.cid)
                    unique_compounds.append(comp)

            direct_results = []
            for comp in unique_compounds[:limit]:
                name = comp.iupac_name or (comp.synonyms[0] if comp.synonyms else query.title())
                cas = None
                try:
                    if getattr(comp, 'cas', None):
                        cas = comp.cas[0] if isinstance(comp.cas, (list, tuple)) and comp.cas else comp.cas
                except Exception:
                    pass
                direct_results.append({
                    "name": name,
                    "cid": comp.cid,
                    "formula": comp.molecular_formula,
                    "mw": comp.molecular_weight,
                    "cas": cas
                })

            if direct_results:
                _cache[q_lower] = direct_results
                _save_cache(_cache)

        except Exception as e:
            print(f"PubChem search error for '{query}': {e}")
            direct_results = []

    # Augment with previously cached chemicals that contain the query string (substring support)
    augmented = list(direct_results)
    seen = set()
    for r in direct_results:
        key = r.get("cid") or r.get("name", "").lower()
        seen.add(key)

    for cached_list in _cache.values():
        for r in cached_list:
            name_lower = r.get("name", "").lower()
            if q_lower in name_lower:
                key = r.get("cid") or name_lower
                if key not in seen:
                    seen.add(key)
                    augmented.append(r)

    # Sort: prefix matches first, then other contains
    def sort_key(r):
        name_lower = r.get("name", "").lower()
        if name_lower.startswith(q_lower):
            return (0, name_lower)
        elif q_lower in name_lower:
            return (1, name_lower)
        else:
            return (2, name_lower)

    augmented.sort(key=sort_key)

    return augmented[:limit]


# --- Vapor pressure / relative volatility estimation ---

try:
    import chemicals
    import chemicals.vapor_pressure as vp
except ImportError:
    chemicals = None
    vp = None


def estimate_psat(name: str, T: float) -> Optional[float]:
    """
    Estimate pure-component vapor pressure (Pa) at T (Kelvin) using the chemicals library
    and corresponding-states methods (Lee-Kesler, Ambrose-Walton, etc.).
    These work from Tc, Pc, acentric factor which are available for a wide range of compounds.
    Returns None on failure (unknown compound or missing critical data).
    """
    if chemicals is None or vp is None or T <= 0:
        return None
    try:
        cas = chemicals.CAS_from_any(name)
        if not cas:
            return None
        Tc = chemicals.Tc(cas)
        Pc = chemicals.Pc(cas)
        omega = chemicals.omega(cas)
        if Tc is None or Pc is None or omega is None:
            return None

        # Try several corresponding-states / generalized methods in order of preference
        methods = [vp.Lee_Kesler, vp.Ambrose_Walton, vp.Edalat, vp.Sanjari]
        for meth in methods:
            try:
                val = meth(T, Tc, Pc, omega)
                if val is not None and val > 0:
                    return float(val)
            except Exception:
                continue

        return None
    except Exception as e:
        print(f"Psat estimation failed for '{name}' at {T} K: {e}")
        return None


def calculate_relative_volatilities(
    chem_names: List[str],
    T: float,
    ref_name: Optional[str] = None
) -> Dict[str, float]:
    """
    Compute ideal relative volatilities at temperature T (K) from Psat ratios:
        alpha_i = Psat_i(T) / Psat_ref(T)
    The reference (usually the heavy key or lowest-volatility component) gets alpha = 1.0.
    If ref_name is not provided or has no Psat, the lowest-Psat compound is chosen as reference.
    Components without data get alpha = 1.0 (neutral) and a warning is implicit (caller decides).
    """
    if not chem_names:
        return {}

    psats: Dict[str, Optional[float]] = {}
    for nm in chem_names:
        ps = estimate_psat(nm, T)
        psats[nm] = ps

    valid_psats = {k: v for k, v in psats.items() if v is not None and v > 0}

    if not valid_psats:
        # No vapor pressure data at all — fall back to unity (user must edit manually)
        return {nm: 1.0 for nm in chem_names}

    if ref_name is None or ref_name not in valid_psats:
        # Choose least volatile (lowest Psat) as reference — conventional for HK = 1.0
        ref_name = min(valid_psats, key=valid_psats.get)

    ref_psat = valid_psats[ref_name]

    alphas: Dict[str, float] = {}
    for nm in chem_names:
        p = psats.get(nm)
        if p and ref_psat > 0:
            alphas[nm] = round(p / ref_psat, 4)
        else:
            alphas[nm] = 1.0
    return alphas


def calculate_relative_volatility(comp1: str, comp2: str, T: float) -> Optional[float]:
    """
    Convenience wrapper: relative volatility of comp1 w.r.t. comp2 at T (K).
    Returns None if data unavailable.
    """
    alphas = calculate_relative_volatilities([comp1, comp2], T, ref_name=comp2)
    val = alphas.get(comp1, 1.0)
    # If both fell back to 1.0 because no data, signal unavailability
    if val == 1.0 and estimate_psat(comp1, T) is None and estimate_psat(comp2, T) is None:
        return None
    return val


# =============================================================================
# Feed thermal condition (q) calculation from temperature
# =============================================================================

def compute_k_values(
    component_names: List[str],
    T: float,
    P_bar: float
) -> Dict[str, float]:
    """
    Compute K-values (y/x) at T (K) and P (bar) using ideal (Raoult's law) model:
    K_i = P^sat_i(T) / P   (from corresponding-states vapor pressure estimation).
    """
    if P_bar <= 0:
        P_bar = 1.0

    P_pa = P_bar * 100_000.0
    kvals: Dict[str, float] = {}

    for name in component_names:
        psat = estimate_psat(name, T)
        kvals[name] = (psat / P_pa) if psat and psat > 0 else 1.0

    return kvals


def _rachford_rice(z_list: List[float], K_list: List[float], max_iter: int = 150) -> float:
    """
    Solve Rachford-Rice for vapor fraction φ (0 to 1 when two-phase).
    If no root exists in [0,1]:
      - f(0) <= 0  → subcooled liquid → return φ=0
      - f(1) >= 0  → superheated vapor → return φ=1
    This is the physically correct handling for thermal condition calculation.
    """
    if not z_list:
        return 0.0

    def f(phi: float) -> float:
        s = 0.0
        for zi, Ki in zip(z_list, K_list):
            den = 1.0 + phi * (Ki - 1.0)
            if abs(den) < 1e-12:
                den = 1e-12 if den >= 0 else -1e-12
            s += zi * (Ki - 1.0) / den
        return s

    f0 = f(0.0)
    f1 = f(1.0)

    # Subcooled: even at φ=0 the material wants to be all liquid
    if f0 <= 0.0:
        return 0.0
    # Superheated: even at φ=1 the material wants to be all vapor
    if f1 >= 0.0:
        return 1.0

    # Two-phase region: there is a root in (0,1). Use bisection.
    lo, hi = 0.0, 1.0
    flo, fhi = f0, f1

    phi = 0.5
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        fm = f(mid)
        if abs(fm) < 1e-9:
            return mid
        if flo * fm <= 0.0:
            hi = mid
            fhi = fm
        else:
            lo = mid
            flo = fm

    return (lo + hi) / 2.0


def compute_feed_quality(
    component_names: List[str],
    z_dict: Dict[str, float],
    T_feed: float,
    P_bar: float
) -> Tuple[float, str, Dict[str, float]]:
    """
    Calculate the feed thermal condition parameter q from actual feed temperature and pressure
    using ideal (Raoult's law) K-values.
    """
    if T_feed <= 10 or P_bar <= 0:
        return 1.0, "Invalid feed T or P", {"phi": 0.0}

    names = list(component_names)
    z_list = [float(z_dict.get(n, 0.0)) for n in names]
    z_tot = sum(z_list)
    if z_tot > 1e-12:
        z_list = [z / z_tot for z in z_list]

    K_dict = compute_k_values(names, T_feed, P_bar)
    K_list = [K_dict.get(n, 1.0) for n in names]

    phi = _rachford_rice(z_list, K_list)

    q = 1.0 - phi

    if phi <= 0.001:
        state = "subcooled liquid"
    elif phi >= 0.999:
        state = "superheated vapor"
    else:
        state = f"two-phase (vapor frac φ={phi:.3f})"

    info = {
        "phi": round(phi, 5),
        "q": round(q, 4),
        "K_values": {k: round(v, 4) for k, v in K_dict.items()},
        "T_feed_K": T_feed,
        "P_bar": P_bar,
        "state": state,
    }

    return round(q, 4), state, info


# =============================================================================
# Simple thermodynamic property estimators for shortcut column
# =============================================================================

def estimate_bubble_point(component_names, z_mole, P_bar, T_guess=350.0, tol=0.1, max_iter=60):
    """Estimate bubble point temperature (K) using ideal (Raoult's law) K-values."""
    if P_bar <= 0:
        P_bar = 1.0

    def objective(T):
        K_dict = compute_k_values(component_names, T, P_bar)
        s = 0.0
        for name, z in zip(component_names, z_mole):
            s += K_dict.get(name, 1.0) * z
        return s - 1.0

    T = T_guess
    for _ in range(max_iter):
        f = objective(T)
        if abs(f) < 0.001:
            return round(T, 1)
        dT = 0.5
        f2 = objective(T + dT)
        deriv = (f2 - f) / dT if abs(dT) > 1e-6 else 0.01
        if abs(deriv) < 1e-6:
            T += 2.0 if f < 0 else -2.0
        else:
            T = T - f / deriv
        T = max(200.0, min(T, 900.0))
    return round(T, 1)


def estimate_dew_point(component_names, z_mole, P_bar, T_guess=350.0, tol=0.1, max_iter=60):
    """Estimate dew point temperature (K) using ideal (Raoult's law) K-values."""
    if P_bar <= 0:
        P_bar = 1.0

    def objective(T):
        K_dict = compute_k_values(component_names, T, P_bar)
        s = 0.0
        for name, z in zip(component_names, z_mole):
            ki = K_dict.get(name, 1.0)
            s += z / ki if ki > 0 else 0.0
        return s - 1.0

    T = T_guess
    for _ in range(max_iter):
        f = objective(T)
        if abs(f) < 0.001:
            return round(T, 1)
        dT = 0.5
        f2 = objective(T + dT)
        deriv = (f2 - f) / dT if abs(dT) > 1e-6 else 0.01
        if abs(deriv) < 1e-6:
            T += 2.0 if f > 0 else -2.0
        else:
            T = T - f / deriv
        T = max(200.0, min(T, 900.0))
    return round(T, 1)


def estimate_average_latent_heat(component_names, z_mole, T):
    """Very rough average heat of vaporization (kJ/kmol) at temperature T."""
    # Use a simple corresponding-states estimate or fixed value per component when possible.
    # For educational use we return a reasonable average (many hydrocarbons ~ 25-40 MJ/kmol).
    total = 0.0
    count = 0
    for name, z in zip(component_names, z_mole):
        # Very crude: 30-38 MJ/kmol is common for light organics. Bias a bit lower for heavier.
        base = 35000.0   # kJ/kmol
        total += z * base
        count += 1
    if count == 0:
        return 35000.0
    return total / count


def get_rich_thermo_properties(name: str) -> Dict[str, float]:
    """
    Retrieve key thermochemical properties needed for different thermodynamic models
    (Tc, Pc, omega, Tb, etc.). Used when user selects non-ideal methods.
    """
    props: Dict[str, float] = {}
    try:
        cas = chemicals.CAS_from_any(name)
        if cas:
            props["cas"] = cas
            tc = chemicals.Tc(cas)
            pc_pa = chemicals.Pc(cas)
            omega = chemicals.omega(cas)
            tb = chemicals.Tb(cas)

            if tc: props["tc"] = float(tc)
            if pc_pa: props["pc_bar"] = float(pc_pa) / 1e5
            if omega is not None: props["omega"] = float(omega)
            if tb: props["tb"] = float(tb)
    except Exception as e:
        print(f"Thermo property lookup limited for {name}: {e}")

    return props


