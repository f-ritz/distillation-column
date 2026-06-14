"""
Chemical Database using the 'chemicals' library
"""

import chemicals
from chemicals import vapor_pressure
from typing import List, Dict, Optional


def search_chemicals(query: str, limit: int = 15) -> List[Dict]:
    try:
        results = chemicals.search_chemicals(query)
        return [{"name": r.name, "CAS": r.CAS, "formula": r.formula} for r in results[:limit]]
    except:
        return []


def calculate_relative_volatility(comp1: str, comp2: str, T: float) -> Optional[float]:
    try:
        chem1 = chemicals.search_chemicals(comp1)[0]
        chem2 = chemicals.search_chemicals(comp2)[0]

        Psat1 = vapor_pressure.T_dependent_property(T=T, Tc=chem1.Tc, Pc=chem1.Pc, omega=chem1.omega)
        Psat2 = vapor_pressure.T_dependent_property(T=T, Tc=chem2.Tc, Pc=chem2.Pc, omega=chem2.omega)

        if Psat1 and Psat2 and Psat2 > 0:
            return Psat1 / Psat2
        return None
    except:
        return None