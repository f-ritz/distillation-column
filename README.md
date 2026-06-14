# FUGK Distillation Calculator

**Reverse-engineered Aspen DSTWU** using the classic Fenske-Underwood-Gilliland-Kirkbride (FUGK) shortcut method.

This tool is designed to be a versatile, standalone application that mimics the behavior of Aspen's Shortcut Distillation (DSTWU) block for preliminary column design — without running a full rigorous simulation like RADFRAC.

## Features

- **Multicomponent support** (up to 10 components)
- **Constant relative volatility** input
- **Feed thermal condition** (q-value: subcooled, saturated, superheated)
- **Recovery specifications** for light and heavy keys
- **Fenske** → Minimum stages (N_min)
- **Underwood** → Minimum reflux (R_min)
- **Gilliland** → Actual stages at operating reflux
- **Kirkbride** → Recommended feed stage location
- **Component distribution** estimates for all species
- Clean **CustomTkinter GUI** (native desktop look & feel)
- Cross-platform (Windows + macOS)

## Installation & Running

### Option 1: Run from source (recommended for development)

```bash
git clone https://github.com/f-ritz/distillation-column.git
cd distillation-column
pip install -r requirements.txt
python gui/app.py
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

1. Define your components and feed mole fractions
2. Enter relative volatilities (α) — usually referenced to the heaviest component
3. Set feed flow rate and thermal condition (q)
4. Choose Light Key (LK) and Heavy Key (HK)
5. Specify desired recoveries in distillate/bottoms
6. Choose operating reflux ratio (R / R_min)
7. Click **Run FUGK Calculation**

The tool outputs:
- N_min and R_min
- Recommended actual stages and reflux
- Feed stage location
- Full component distribution table
- Estimated product compositions

## Limitations & Notes

- This is a **shortcut method** (like Aspen DSTWU), not rigorous stage-by-stage simulation.
- Assumes constant relative volatility (no temperature-dependent K-values in v1).
- Non-key component splits are estimated via Fenske distribution.
- Best used for **preliminary design**, feasibility studies, and education.
- For final design, always validate with rigorous simulation (Aspen RADFRAC, DWSIM, etc.).

## References

- Fenske (1932) — Minimum stages at total reflux
- Underwood (1948) — Minimum reflux
- Gilliland (1940) — Actual stages vs. minimum
- Kirkbride (1944) — Feed stage location

## License

MIT License — feel free to use, modify, and distribute.

## Author

Built as an open educational tool for chemical engineers who want a fast, transparent shortcut distillation calculator.