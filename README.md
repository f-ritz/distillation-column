# Distillation Calculator (Fenske-Underwood-Gilliland-Kirkbride)

A simple, standalone desktop tool for preliminary multicomponent distillation column design using the classic **Fenske-Underwood-Gilliland-Kirkbride (FUGK)** shortcut method.

The app uses **only the Ideal (Raoult's law)** model: K-values are computed from pure-component vapor pressures estimated via the `chemicals` library (corresponding-states methods) at the column pressure. It supports molar or mass feed flow, mole or mass composition (with automatic conversion using molecular weights), derives the feed thermal condition (q) from your specified Feed Temperature + Pressure via a Rachford-Rice flash, calculates condenser and reboiler duties with proper thermodynamic sign convention, reports Kirkbride feed stage locations for **both** the minimum-stage case and the actual operating case, and gives preliminary column sizing (height + diameter) with user-adjustable tray spacing.

**This is a first-pass approximation tool only.** It assumes ideal vapor-liquid equilibrium (Raoult's Law) at all times. Real mixtures with non-idealities (azeotropes, activity coefficients significantly different from 1, etc.) will produce incorrect results. Always double-check important designs with a rigorous simulator (Aspen RADFRAC, DWSIM, ChemCAD, etc.).

## Features

- **Multicomponent support** (binary up to ~10 components)
- **Chemical search** via PubChem (name or CAS) + local cache augmentation for substring "contains" matches. Dropdown shows rich labels: Preferred Name (Formula) [CAS: ...]
- **Only Ideal / Raoult's law** for all VLE and thermal calculations: K_i = P^sat_i(T) / P using vapor-pressure estimates from the `chemicals` library (no activity-coefficient models, no NRTL/Wilson/PR/SRK, no model selector)
- **Feed input flexibility**:
  - Total feed flow in kmol/h (molar) or kg/h (mass)
  - Composition in mole fractions or mass fractions (switching basis auto-converts the table using stored molecular weights)
  - "Normalize to 1.0" button for the composition
  - Live Σz indicator (green when valid, red when off)
- **Feed Temperature (K) + Column Pressure (bar) → q**: the feed thermal condition is computed internally via Rachford-Rice isothermal flash using ideal K-values at the given T and P. No manual q field.
- **Light Key (LK) / Heavy Key (HK)** selection via dropdowns or "Set row as LK/HK" buttons (higher α = lighter/more volatile)
- **Separation specs**: LK recovery in distillate, HK recovery in bottoms, operating reflux ratio R/R_min (typical 1.1–1.5)
- **User-specified tray spacing** (inches or mm, default 24 in) for height estimate
- **Full FUGK + duties + sizing results**:
  - Fenske N_min, Underwood R_min (proper multicomponent theta-root bisection), Gilliland N_actual, operating R
  - **Kirkbride optimal feed stage reported for both cases**: feed_stage_min (at total reflux / N_min) and feed_stage_actual (at the operating N_actual)
  - Component molar flows in D and B, recoveries, and product mole fractions xD / xB
  - Total distillate and bottoms flows (kmol/h + kg/h)
  - Estimated top temperature (dew point) and bottom temperature (bubble point) using ideal model
  - Condenser duty (negative = heat removed) and reboiler duty (positive = heat added) with explicit sign convention and warning if reboiler duty comes out negative
  - Preliminary column height (N_actual × tray spacing + allowances) and diameter (rough flooding/velocity estimate on rectifying vapor flow)
- Clean **CustomTkinter GUI** with clear 1-2-3-4 workflow sections on the left, large calculate button, live results pane, CSV export, copy results, Load Example presets, and α re-estimation at a chosen reference temperature
- Window title: "Distillation calculator"
- Cross-platform (Windows + macOS). Linux support dropped (user preference).
- Standalone single-file executables via PyInstaller (no Python required to run the release)

## How to Use

### For most people: just download a release and run it

1. Go to the **Releases** page of this repository on GitHub (look for the "Releases" tab or https://github.com/f-ritz/distillation-column/releases).
2. Download the latest asset:
   - Windows: `Distillation_Calculator.exe` (single-file executable, ~80+ MB)
   - macOS: the corresponding app or zip for your architecture
3. On Windows the first time you run it you may see a Windows Defender SmartScreen warning — click "More info" → "Run anyway".
4. Double-click the executable. The app opens directly (no installer, no Python needed).
5. Use the GUI (detailed steps below). When done, just close the window.

**Important — this is a first-pass approximation calculator only.**  
The results are useful for education, quick feasibility checks, and preliminary design work.  
**Always double-check important numbers with a more rigorous simulator** (Aspen Plus RADFRAC / DSTWU verification, DWSIM, ChemCAD, HYSYS, etc.) before using them for real engineering decisions, equipment purchase, or safety-related work. The tool uses only ideal (Raoult's law) VLE and many shortcut approximations for duties and sizing.

### Detailed GUI workflow (once the app is running)

The left side of the window is organized into clear numbered sections that match the calculation flow.

**1. Add Chemicals (search PubChem by name or CAS)**  
- Type a chemical name or CAS number into the search box and click **Search**.  
- Results appear in the dropdown with rich labels: `Preferred Name (Formula) [CAS: xxxxx]`.  
- The search supports substring "contains" matches thanks to local cache augmentation (e.g. typing "benz" will surface Benzene and related). CAS namespace is tried automatically when the query looks like a CAS number.  
- Select a result and click **Add Chemical**. It is added with a default z and an α estimated from real vapor-pressure data at the α Ref T (K) shown above the table.  
- Repeat for all components (minimum 2).  
- The table shows Name | z (Feed frac) | α (rel). Higher α = more volatile (lighter) component.  
- Use **Edit z**, **Remove**, **Clear All**, or the big green **Normalize to 1.0** button. The live `Σ z = ...` label turns green when the sum is acceptably close to 1.0 and red otherwise.  
- You can switch the composition basis between "Mole fractions" and "Mass fractions"; the table values convert automatically using the stored molecular weights.  
- The total feed flow basis (kmol/h vs kg/h) is independent — choose whichever is convenient; internal calculations are always on a consistent molar basis.

**2. Feed Conditions**  
- Enter the **Total Feed** value and pick the basis with the combobox (kmol/h (molar) or kg/h (mass)).  
- Set **Composition as:** (Mole fractions / Mass fractions) — this controls what the numbers in the chemicals table currently represent.  
- **Feed Temperature (K)** — this is the key new input. The app uses it (plus pressure and composition) to compute the feed quality q via a Rachford-Rice flash with ideal K-values.  
- **Feed / Column Pressure (bar)** — used for K-values, q, bubble/dew point estimates, and the rough diameter calculation. Typical atmospheric column = 1.0 bar.

**3. Keys & Separation Targets**  
- Choose or set the **Light Key (LK)** and **Heavy Key (HK)** using the dropdowns or the "Set row as LK" / "Set row as HK" buttons next to the table.  
  - Convention: the component with the higher α should be the LK.  
- Enter the desired recoveries:  
  - LK recovery in Distillate (e.g. 0.99 = 99 % of the LK goes to the top product)  
  - HK recovery in Bottoms (e.g. 0.99)  
- Set the **Operating R / R_min** (recommended starting value 1.3; typical industrial range 1.1 – 1.5).

**4. Column Sizing Parameters**  
- Set **Tray spacing** (default 24 inches). You can also choose mm. This value only affects the height estimate.

**Calculate**  
Click the large blue button:  
**🚀 Calculate Column (Fenske-Underwood-Gilliland-Kirkbride + Duties + Sizing)**

The right-hand pane populates with a detailed text report containing:

- The input summary and the derived q + feed state (subcooled liquid / two-phase / superheated vapor).
- FUGK numbers: N_min, R_min, N_actual (at your chosen R/Rmin), operating R.
- **Two feed-stage recommendations from the Kirkbride correlation**:
  - feed stage at minimum stages (total reflux case)
  - feed stage at the actual operating number of stages
- Distillate and bottoms total flows (molar + mass), estimated top and bottom temperatures.
- Duties with sign convention: condenser duty is shown negative (heat leaving the system), reboiler duty positive (heat entering). A warning block appears if the reboiler duty is negative.
- Preliminary height and diameter.
- Full component-by-component split table and product compositions.
- Tray-numbering and height-basis notes (Tray #1 is the top tray; reboiler counts as the last stage; condenser does not count as a tray).

Use the **📋 Copy Results** and **💾 Export CSV** buttons to capture the output. The **Load Example** button restores a classic Benzene-Toluene (or other) preset for quick experimentation. The **Re-estimate α at T** / "Re-estimate all α at this T" buttons let you update all relative volatilities after changing the reference temperature in the α Ref T box.

**Window title** while running: "Distillation calculator"

That's it — enter your data, hit Calculate, review the numbers, then validate externally.

## Running from source (for developers / customization)

```bash
git clone https://github.com/f-ritz/distillation-column.git
cd distillation-column
pip install -r requirements.txt
python gui/app.py
# or simply
python run.py
```

The core math lives in `core/fug.py`; the GUI and all feed-basis / q-from-T / duty / sizing logic is in `gui/app.py`. Chemical search + ideal K-values + q flash live in `core/chemical_database.py`.

To run the unit tests (note: they are minimal):
```bash
python -m pytest tests/ -q
# or the quick smoke test shown in the old README
```

## Building standalone executables (Windows + macOS)

Use the helper script (recommended):

```bash
pip install pyinstaller
python build_executable.py
```

This produces `dist/Distillation_Calculator.exe` (or macOS equivalent). It bundles:
- icon.png (runtime window + taskbar/dock icon on all platforms)
- icon.ico when present (for the Windows .exe file icon via --icon and for iconbitmap inside the app)

See `build_executable.py` for the exact PyInstaller flags and icon handling. Linux builds are not supported in the script (per earlier preference).

After a build you may still need the usual SmartScreen / "damaged app" steps on first run of the new binary.

## Limitations & Notes

- This is a **shortcut method** (Fenske-Underwood-Gilliland-Kirkbride), **not** a rigorous stage-by-stage equilibrium-stage simulation. It is intended for education, quick scoping, and first-pass estimates only.
- **Only ideal / Raoult's law** VLE is used everywhere (K_i = P^sat_i(T) / P from corresponding-states vapor pressure estimates). There is no support for activity-coefficient models, azeotropes, or strong non-ideality. Real industrial mixtures frequently deviate from ideality — results can be substantially wrong.
- Relative volatilities (α) are treated as **constant** (evaluated at the single reference temperature you choose). Real systems have temperature-dependent α.
- Non-key component distributions use the Fenske equation evaluated at N_min (standard shortcut practice).
- Duties and preliminary sizing (height, diameter) are very approximate energy-balance and hydraulic shortcuts. The condenser is assumed total. A warning is shown when the calculated reboiler duty is negative (physically unusual).
- **Both Kirkbride feed stages are reported** so you can see the difference between the total-reflux location and the operating-case location.
- Tray numbering convention (documented in every result): Tray #1 = top tray; reboiler counts as the last equilibrium stage; total condenser does not count as a tray. Height includes documented allowances for vapor space, sump, etc.
- **Always double-check with a rigorous simulator** (Aspen RADFRAC, DWSIM, etc.) before using numbers for design, procurement, or anything that matters. This tool is a fast transparent first-pass approximation calculator.

Best used for teaching the FUGK method, quick "what if" studies, and as a transparent reference implementation.

## References

### FUGK Method
- Fenske (1932) — Minimum stages at total reflux
- Underwood (1948) — Minimum reflux
- Gilliland (1940) — Actual stages vs. minimum
- Kirkbride (1944) — Feed stage location

### Data Sources & Thermodynamic Basis
- **PubChem** (https://pubchem.ncbi.nlm.nih.gov/) — Primary source for chemical identity, preferred names, formulas, CAS numbers, molecular weights, and synonyms. Accessed at runtime via the PubChemPy package. Search supports both name and CAS namespaces; previously-seen results are cached locally to enable substring "contains" matches even when offline.
- **chemicals** Python package (https://github.com/CalebBell/chemicals) — Supplies critical constants (Tc, Pc, ω) and the vapor-pressure estimation routines (Lee-Kesler, Ambrose-Walton, etc.). **All K-values, q calculations, bubble/dew points, and relative volatilities are computed under the strict ideal / Raoult's law assumption**:
  K_i = P^sat_i(T) / P
  (no Poynting correction, no vapor fugacity coefficients, no liquid activity coefficients).

**Strong warning**: Because every thermodynamic calculation in this app assumes ideal Raoult's-law behavior, results for real mixtures that show positive/negative deviations, azeotropes, or activity coefficients far from unity can be significantly in error. This tool is intended only for preliminary design, education, and rapid feasibility screening. **Always validate important results with a rigorous simulator** (Aspen RADFRAC, DWSIM, etc.).

## License

MIT License — feel free to use, modify, and distribute.

## Icon (cross-platform)

The app tries hard to show a custom icon both in the window title bar and in the OS taskbar / dock.

- `icon.png` (in project root) is bundled and used at runtime for the title bar + taskbar/dock on Windows and macOS.
- On Windows, if `icon.ico` is also present it is preferred for `iconbitmap` (best taskbar behavior) and is passed to PyInstaller's `--icon` so the .exe itself shows the icon in Explorer.
- The build script (`build_executable.py`) automatically adds the icon files when they exist.

If no custom icon files are found the app falls back to the default Python / Tk icon.

(Place `icon.png` and/or `icon.ico` in the project root next to `gui/`, `core/`, `build_executable.py`, etc.)

## Author

Built as an open educational tool for chemical engineers who want a fast, transparent shortcut distillation calculator that you can actually run without installing a huge process simulator. MIT license — contributions and feedback welcome.