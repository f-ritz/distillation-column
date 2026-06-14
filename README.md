# FUGK Distillation Calculator

**Reverse-engineered Aspen DSTWU** using the classic Fenske-Underwood-Gilliland-Kirkbride (FUGK) shortcut method.

This tool is designed to be a versatile, standalone application that mimics the behavior of Aspen's Shortcut Distillation (DSTWU) block for preliminary column design — without running a full rigorous simulation like RADFRAC.

## Features

- **Multicomponent support**
- **Automatic relative volatility estimation** (ideal Psat ratios via corresponding-states methods from the `chemicals` library at user-specified T)
- **Fully editable** feed mole fractions (z) and relative volatilities (α)
- **Explicit Light Key / Heavy Key selection** (not limited to first/last)
- **Feed thermal condition** (q-value: subcooled, saturated, superheated)
- **Recovery specifications** for light and heavy keys
- **Proper Underwood** minimum reflux (numerical root solve) + classic Fenske N_min, Gilliland N, Kirkbride feed location
- **Component distribution** estimates for all species (Fenske for non-keys)
- Clean **CustomTkinter GUI** (native desktop look & feel) with presets, CSV export, and copy-to-clipboard
- Cross-platform (Windows + macOS)
- Standalone executable build support (PyInstaller)

## Installation & Running

### Option 1: Run from source (recommended for development)

```bash
git clone https://github.com/f-ritz/distillation-column.git
cd distillation-column
pip install -r requirements.txt
python gui/app.py
# or
python run.py
```

Run tests:
```bash
python -c "
import sys
sys.path.insert(0, '.')
from tests.test_fug import *
test_basic_binary_bt(); test_multicomponent_and_nonkeys()
print('Core tests OK')
"
```

### Option 2: Build standalone executable (Windows + macOS)

You can package the tool into a single standalone executable using PyInstaller. This creates a file you can run without installing Python.

#### Recommended method (uses the included build script)

```bash
pip install pyinstaller
python build_executable.py
```

The executable will be created in the `dist/` folder.

#### Manual build commands

**On Windows (PowerShell or CMD):**
```powershell
pyinstaller --onefile --windowed --name "FUGK_Distillation_Calculator" gui/app.py
```

**On macOS (Terminal):**
```bash
pyinstaller --onefile --windowed --name "FUGK_Distillation_Calculator" gui/app.py
```

After building:
- The executable will be in the `dist/` folder.
- On **macOS**, if you get a "damaged" or "cannot be opened" warning, right-click the app → Open (or run `xattr -cr dist/FUGK_Distillation_Calculator` in Terminal).
- On **Windows**, you may need to allow the .exe through Windows Defender SmartScreen the first time.

#### Notes
- The first build can take a minute or two.
- The resulting executable is self-contained (includes Python + all dependencies).
- For a smaller file size or faster startup, you can experiment with `--exclude-module` flags later.

## How to Use

1. Search and add chemicals (PubChem lookup + local cache). The first added becomes a starting point for LK/HK.
2. Feed fractions (z) and relative volatilities (α) are populated automatically. α are estimated at the T you specify using real vapor-pressure methods (higher α = lighter/more volatile).
3. Click rows in the table and use **Set Selected as LK** / **HK**, or pick from the dropdowns. You can manually **Edit z** or **Edit α** at any time. Use the **Normalize Σz→1** button anytime the fractions get messy.
4. Set feed flow + **Feed Temperature (K)**. Then click **"Calc q from T_feed + P"** — the program will perform an isothermal flash (using real Psat data + Rachford-Rice) and automatically fill the Feed Quality q field with the correct thermal condition (q=1 subcooled, 0<q<1 two-phase, q=0 superheated vapor, etc.).
5. Pressure is used for the q calculation (and shown in results). You can still manually override q if you prefer.
6. Set desired key recoveries and operating R/Rmin (typical 1.1–1.5).
5. (Optional) Click **Load Example** for a realistic starting case, or **Recalc α (use HK ref)** after changing temperature.
6. Click **🚀 Calculate FUGK**.

The tool outputs:
- N_min (Fenske) and R_min (Underwood)
- Recommended actual stages (Gilliland) and operating reflux
- Recommended feed stage location (Kirkbride)
- Full component flow + recovery + product composition table
- Warnings when assumptions are stressed (very low α, etc.)

Use the **Export CSV** button for documentation or further analysis in Excel.

## Limitations & Notes

- This is a **shortcut method** (like Aspen DSTWU), not rigorous stage-by-stage simulation (use RADFRAC / equivalent for final design).
- Relative volatilities are assumed **constant** (computed at a single reference T). Real systems have temperature-dependent α.
- Non-key component splits are estimated via Fenske at N_min.
- The Underwood solver uses a robust bisection; edge cases with very close-boiling keys (α_LK/HK < 1.1) or extreme q may need manual review.
- Ideal VLE is implicit. Highly non-ideal systems (azeotropes, strong activity coeffs) will need adjustment or rigorous tools.
- Best used for **preliminary design**, feasibility studies, and education. Always validate with rigorous simulation (Aspen, DWSIM, etc.).

## References

- Fenske (1932) — Minimum stages at total reflux
- Underwood (1948) — Minimum reflux
- Gilliland (1940) — Actual stages vs. minimum
- Kirkbride (1944) — Feed stage location

## License

MIT License — feel free to use, modify, and distribute.

## Author

Built as an open educational tool for chemical engineers who want a fast, transparent shortcut distillation calculator.