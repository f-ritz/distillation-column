"""
Fenske-Underwood-Gilliland-Kirkbride (FUGK) Distillation Calculator
- Chemical search via PubChem + local cache
- Automatic relative volatility (Psat via corresponding states)
- Editable z and α + selectable Light/Heavy keys
- Proper multicomponent Fenske-Underwood-Gilliland-Kirkbride (Underwood min reflux)
- Feed T/P driven q calculation with molar/mass basis support
- Reboiler/condenser duties with proper sign convention
- Preliminary column sizing (height/diameter)
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import sys
import os
import csv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.fug import FUGKDistillation
from core.chemical_database import (
    search_chemicals,
    calculate_relative_volatilities,
    calculate_relative_volatility,
    compute_feed_quality,
    estimate_bubble_point,
    estimate_dew_point,
    estimate_average_latent_heat,
)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class FUGKApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Distillation calculator")
        self.geometry("1250x900")
        self.minsize(1150, 750)

        # Cross-platform icon support (icon.png for runtime title bar + dock/taskbar)
        # Place icon.png in the project root.
        # For best Windows results (taskbar + .exe file icon), also provide icon.ico
        # and the build script will use it.
        try:
            import os
            import sys
            import tkinter as tk

            # Works in source and in PyInstaller bundles (onefile uses _MEIPASS)
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            # Prefer .ico on Windows for best taskbar compatibility
            icon_path = None
            if sys.platform.startswith("win"):
                ico_path = os.path.join(base_dir, "icon.ico")
                if os.path.exists(ico_path):
                    icon_path = ico_path
                else:
                    png_path = os.path.join(base_dir, "icon.png")
                    if os.path.exists(png_path):
                        icon_path = png_path
            else:
                png_path = os.path.join(base_dir, "icon.png")
                if os.path.exists(png_path):
                    icon_path = png_path

            # Dev fallback
            if not icon_path or not os.path.exists(icon_path):
                cwd_icon = os.path.join(os.getcwd(), "icon.png")
                if os.path.exists(cwd_icon):
                    icon_path = cwd_icon

            if icon_path and os.path.exists(icon_path):
                if icon_path.lower().endswith(".ico"):
                    # On Windows, iconbitmap with .ico is the most reliable for both title bar and taskbar
                    # when the .exe was built with --icon
                    self.iconbitmap(icon_path)
                else:
                    # PNG for cross-platform title bar (and dock/taskbar on mac/linux)
                    icon = tk.PhotoImage(file=icon_path)
                    self._icon_image = icon  # keep reference - very important!
                    self.after(0, lambda: self.iconphoto(True, self._icon_image))
            else:
                print(f"[Icon] No icon file found (checked {base_dir} for .ico or .png)")

            # Helps Windows show the custom taskbar icon reliably
            if sys.platform.startswith("win"):
                try:
                    import ctypes
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                        "distillation.calculator"
                    )
                except Exception:
                    pass

        except Exception as e:
            print(f"[Icon] Failed to set icon: {e}")

        self.chemicals = []   # list of {"name": str, "z": float, "alpha": float, "mw": float}
        self.lk_name: str = ""
        self.hk_name: str = ""
        self.last_results = None  # store for export
        self.last_search_results = []  # full search dicts for mw etc.

        self.create_widgets()
        # Initial state for sum label
        if hasattr(self, "z_sum_label"):
            self.z_sum_label.configure(text="Σ z = 0.0000", text_color="gray")

    def create_widgets(self):
        # Title
        title_frame = ctk.CTkFrame(self)
        title_frame.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(title_frame, text="🧪 Distillation Calculator",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=5)

        main = ctk.CTkScrollableFrame(self)
        main.pack(fill="both", expand=True, padx=10, pady=5)

        left = ctk.CTkFrame(main)
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right = ctk.CTkFrame(main)
        right.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # === CHEMICAL SEARCH ===
        ctk.CTkLabel(left, text="1. Add Chemicals (search PubChem by name or CAS; results show preferred name + formula + CAS)", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=8, anchor="w", padx=10)

        search_frame = ctk.CTkFrame(left)
        search_frame.pack(fill="x", padx=10, pady=3)

        self.search_entry = ctk.CTkEntry(search_frame, width=200, placeholder_text="Search by name or CAS...")
        self.search_entry.pack(side="left", padx=5)

        ctk.CTkButton(search_frame, text="Search", command=self.search_chemical, width=70).pack(side="left")

        self.search_results = ctk.CTkComboBox(search_frame, width=280, values=["Search results will appear here"])
        self.search_results.pack(side="left", padx=5)

        # Temperature + Add + Recalculate
        add_frame = ctk.CTkFrame(left)
        add_frame.pack(fill="x", padx=10, pady=3)

        ctk.CTkLabel(add_frame, text="α Ref T (K):").pack(side="left", padx=5)
        self.temp_entry = ctk.CTkEntry(add_frame, width=70)
        self.temp_entry.insert(0, "353")
        self.temp_entry.pack(side="left", padx=5)

        ctk.CTkButton(add_frame, text="Add Chemical", command=self.add_chemical,
                      fg_color="#2E7D32", width=105).pack(side="left", padx=5)

        ctk.CTkButton(add_frame, text="Re-estimate all α at this T", command=self.recalculate_alphas,
                      fg_color="#1565C0", width=175).pack(side="left", padx=5)

        # Current chemicals table
        ctk.CTkLabel(left, text="Chemicals (Step A) — α estimated automatically from T below using real vapor pressure data",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(pady=6, anchor="w", padx=10)

        self.tree = ttk.Treeview(left, columns=("Name", "z (Feed frac)", "α (rel)"), show="headings", height=8)
        self.tree.pack(fill="x", padx=10, pady=5)

        self.tree.heading("Name", text="Name")
        self.tree.heading("z (Feed frac)", text="z (Feed frac)")
        self.tree.heading("α (rel)", text="α (rel)")

        self.tree.column("Name", width=180)
        self.tree.column("z (Feed frac)", width=120)
        self.tree.column("α (rel)", width=100)

        self.z_sum_label = ctk.CTkLabel(
            left, text="Σ z = 1.0000", font=ctk.CTkFont(size=11, weight="bold")
        )
        self.z_sum_label.pack(anchor="w", padx=12, pady=(0, 2))

        btn_frame = ctk.CTkFrame(left)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="Edit z", command=self.edit_z, width=80).pack(side="left")
        ctk.CTkButton(btn_frame, text="Remove", command=self.remove_selected, fg_color="#C62828", width=80).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Clear All", command=self.clear_all, fg_color="#B71C1C", width=85).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Normalize to 1.0", command=self.normalize_feed, width=115, fg_color="#00695C").pack(side="left", padx=4)

        # === FEED CONDITIONS (Step B) ===
        ctk.CTkLabel(left, text="2. Feed Conditions (T, P, flow, composition)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=6, anchor="w", padx=10)

        feed_frame = ctk.CTkFrame(left)
        feed_frame.pack(fill="x", padx=10, pady=3)

        # Total flow + basis
        ctk.CTkLabel(feed_frame, text="Total Feed:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.feed_flow = ctk.CTkEntry(feed_frame, width=85)
        self.feed_flow.insert(0, "100")
        self.feed_flow.grid(row=0, column=1, padx=3)

        self.flow_basis = ctk.CTkComboBox(feed_frame, values=["kmol/h (molar)", "kg/h (mass)"], width=120)
        self.flow_basis.set("kmol/h (molar)")
        self.flow_basis.grid(row=0, column=2, padx=3)
        ctk.CTkLabel(feed_frame, text="← choose units", font=ctk.CTkFont(size=9), text_color="gray").grid(row=0, column=3, sticky="w")

        # Composition basis
        ctk.CTkLabel(feed_frame, text="Composition as:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.comp_basis = ctk.CTkComboBox(feed_frame, values=["Mole fractions", "Mass fractions"], width=130, command=self.on_comp_basis_changed)
        self.comp_basis.set("Mole fractions")
        self.comp_basis.grid(row=1, column=1, columnspan=2, padx=3, sticky="w")
        ctk.CTkLabel(feed_frame, text="(table updates on change)", font=ctk.CTkFont(size=9), text_color="gray").grid(row=1, column=3, sticky="w")

        # Temperature and Pressure - critical for q calculation
        ctk.CTkLabel(feed_frame, text="Feed Temperature (K):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.feed_temp = ctk.CTkEntry(feed_frame, width=85)
        self.feed_temp.insert(0, "355")
        self.feed_temp.grid(row=2, column=1, padx=3)
        ctk.CTkLabel(feed_frame, text="← used to derive feed condition + duties + T_top/T_bot", font=ctk.CTkFont(size=9), text_color="gray").grid(row=2, column=2, columnspan=2, sticky="w")

        ctk.CTkLabel(feed_frame, text="Feed / Column Pressure (bar):").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.pressure = ctk.CTkEntry(feed_frame, width=85)
        self.pressure.insert(0, "1.0")
        self.pressure.grid(row=3, column=1, padx=3)
        ctk.CTkLabel(feed_frame, text="← used for K-values, q, and sizing", font=ctk.CTkFont(size=9), text_color="gray").grid(row=3, column=2, columnspan=2, sticky="w")

        # === 3. KEYS + SEPARATION TARGETS (Step C) ===
        ctk.CTkLabel(left, text="3. Keys & Separation Targets (recoveries define the split)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=6, anchor="w", padx=10)

        # LK/HK selector (already existed, kept for workflow)
        key_frame = ctk.CTkFrame(left)
        key_frame.pack(fill="x", padx=10, pady=3)

        ctk.CTkLabel(key_frame, text="Light Key (LK):", width=100).grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.lk_combo = ctk.CTkComboBox(key_frame, values=["(add chemicals)"], width=200, command=self._on_lk_changed)
        self.lk_combo.grid(row=0, column=1, padx=4, pady=2)
        ctk.CTkButton(key_frame, text="Set row as LK", width=105, command=self.set_selected_as_lk).grid(row=0, column=2, padx=4)

        ctk.CTkLabel(key_frame, text="Heavy Key (HK):", width=100).grid(row=1, column=0, sticky="w", padx=4, pady=2)
        self.hk_combo = ctk.CTkComboBox(key_frame, values=["(add chemicals)"], width=200, command=self._on_hk_changed)
        self.hk_combo.grid(row=1, column=1, padx=4, pady=2)
        ctk.CTkButton(key_frame, text="Set row as HK", width=105, command=self.set_selected_as_hk).grid(row=1, column=2, padx=4)

        ctk.CTkLabel(key_frame, text="Higher α = more volatile (lighter component)", font=ctk.CTkFont(size=9), text_color="gray").grid(row=2, column=0, columnspan=3, sticky="w", padx=4)

        # Recovery specs (still required for FUG method)
        rec_frame = ctk.CTkFrame(left)
        rec_frame.pack(fill="x", padx=10, pady=3)

        ctk.CTkLabel(rec_frame, text="LK recovery in Distillate:").grid(row=0, column=0, sticky="w", padx=5)
        self.lk_rec = ctk.CTkEntry(rec_frame, width=80)
        self.lk_rec.insert(0, "0.99")
        self.lk_rec.grid(row=0, column=1, padx=5)
        ctk.CTkLabel(rec_frame, text="(e.g. 0.99 = 99%)", font=ctk.CTkFont(size=9), text_color="gray").grid(row=0, column=2, sticky="w")

        ctk.CTkLabel(rec_frame, text="HK recovery in Bottoms:").grid(row=1, column=0, sticky="w", padx=5)
        self.hk_rec = ctk.CTkEntry(rec_frame, width=80)
        self.hk_rec.insert(0, "0.99")
        self.hk_rec.grid(row=1, column=1, padx=5)
        ctk.CTkLabel(rec_frame, text="(e.g. 0.99 = 99%)", font=ctk.CTkFont(size=9), text_color="gray").grid(row=1, column=2, sticky="w")

        ctk.CTkLabel(rec_frame, text="Operating R / R_min:").grid(row=2, column=0, sticky="w", padx=5)
        self.r_ratio = ctk.CTkEntry(rec_frame, width=80)
        self.r_ratio.insert(0, "1.30")
        self.r_ratio.grid(row=2, column=1, padx=5)
        ctk.CTkLabel(rec_frame, text="(typical 1.1 – 1.5)", font=ctk.CTkFont(size=9), text_color="gray").grid(row=2, column=2, sticky="w")

        # === 4. COLUMN SIZING (user control) ===
        ctk.CTkLabel(left, text="4. Column Sizing Parameters",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=6, anchor="w", padx=10)

        size_frame = ctk.CTkFrame(left)
        size_frame.pack(fill="x", padx=10, pady=3)

        ctk.CTkLabel(size_frame, text="Tray spacing:").grid(row=0, column=0, sticky="w", padx=5)
        self.tray_spacing = ctk.CTkEntry(size_frame, width=70)
        self.tray_spacing.insert(0, "24")
        self.tray_spacing.grid(row=0, column=1, padx=4)
        self.tray_spacing_units = ctk.CTkComboBox(size_frame, values=["inches", "mm"], width=70)
        self.tray_spacing_units.set("inches")
        self.tray_spacing_units.grid(row=0, column=2, padx=3)
        ctk.CTkLabel(size_frame, text="Default 24 in (610 mm). Affects height only.", font=ctk.CTkFont(size=9), text_color="gray").grid(row=0, column=3, sticky="w")

        # Action buttons + big Calculate
        action_row = ctk.CTkFrame(left)
        action_row.pack(fill="x", padx=10, pady=6)

        ctk.CTkButton(action_row, text="Load Example", command=self.load_example, width=105, fg_color="#455A64").pack(side="left")
        ctk.CTkButton(action_row, text="Re-estimate α at T", command=self.recalculate_alphas, width=140, fg_color="#1565C0").pack(side="left", padx=6)

        ctk.CTkButton(left, text="🚀 Calculate Column (Fenske-Underwood-Gilliland-Kirkbride + Duties + Sizing)",
                      command=self.calculate,
                      fg_color="#1565C0", height=50, font=ctk.CTkFont(size=15, weight="bold")).pack(pady=8, padx=10, fill="x")

        # === RESULTS ===
        ctk.CTkLabel(right, text="Results", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=4)
        self.results_box = ctk.CTkTextbox(right, height=420, width=520)
        self.results_box.pack(padx=10, pady=4)

        res_btns = ctk.CTkFrame(right)
        res_btns.pack(fill="x", padx=10, pady=4)
        ctk.CTkButton(res_btns, text="📋 Copy Results", command=self.copy_results, width=140).pack(side="left")
        ctk.CTkButton(res_btns, text="💾 Export CSV", command=self.export_csv, width=130, fg_color="#2E7D32").pack(side="left", padx=8)
        ctk.CTkButton(res_btns, text="Clear Output", command=lambda: self.results_box.delete("1.0", "end"), width=110).pack(side="left")



    # ==================== CHEMICAL MANAGEMENT ====================
    def search_chemical(self):
        q = self.search_entry.get().strip()
        if not q:
            return
        results = search_chemicals(q)
        if results:
            # Rich display so user knows exactly what identifier / name will be used for the chemical
            # Format: "Preferred Name (Formula) [CAS: xxxxx]"
            display_values = []
            self._search_map = {}  # display -> clean name (used for add + property lookup)
            for r in results:
                name = r.get("name", q)
                formula = r.get("formula", "?")
                cas = r.get("cas")
                cas_part = f" [CAS: {cas}]" if cas else ""
                display = f"{name} ({formula}){cas_part}"
                display_values.append(display)
                self._search_map[display] = name

            self.search_results.configure(values=display_values)
            self.last_search_results = results   # keep full info (incl. mw, cas, etc.) for adding
            if display_values:
                self.search_results.set(display_values[0])
        else:
            messagebox.showinfo("No Results", f"No chemicals found for '{q}'")

    def add_chemical(self):
        selected = self.search_results.get()
        # Use the clean name from our map (strips the formula/CAS suffix we added for display)
        name = self._search_map.get(selected, selected) if hasattr(self, "_search_map") else selected

        if not name or "Search results" in name:
            messagebox.showwarning("Select Chemical", "Please search and select a chemical.")
            return

        try:
            T = float(self.temp_entry.get())
        except:
            T = 353.15

        # Determine reference for new alpha (prefer HK if already chosen and present)
        ref = None
        if self.hk_name and self.hk_name in [c["name"] for c in self.chemicals]:
            ref = self.hk_name
        elif self.chemicals:
            ref = self.chemicals[-1]["name"]  # fallback to last added

        if ref and ref != name:
            alpha = calculate_relative_volatility(name, ref, T) or 1.0
        else:
            alpha = 1.0

        z = 1.0 / (len(self.chemicals) + 1) if self.chemicals else 0.5

        # Capture MW from the most recent search
        mw = 100.0
        for r in getattr(self, "last_search_results", []):
            if r.get("name") == name:
                mw = r.get("mw") or r.get("MW") or 100.0
                break

        self.chemicals.append({
            "name": name,
            "z": round(z, 4),
            "alpha": round(alpha, 4),
            "mw": float(mw) if mw else 100.0
        })

        # If this is the first chemical, make it both for now (user will pick keys)
        if len(self.chemicals) == 1:
            self.lk_name = name
            self.hk_name = name

        self.refresh_table()

    def recalculate_alphas(self):
        """Recalculate α for all chemicals. Reference = selected HK (or lowest alpha)."""
        if len(self.chemicals) < 2:
            messagebox.showinfo("Info", "Need at least 2 chemicals to compute relative volatilities.")
            return

        try:
            T = float(self.temp_entry.get())
        except:
            T = 353.15

        names = [c["name"] for c in self.chemicals]
        ref = self.hk_name if self.hk_name in names else None

        alphas = calculate_relative_volatilities(names, T, ref_name=ref)

        changed = 0
        for chem in self.chemicals:
            new_a = alphas.get(chem["name"], chem["alpha"])
            if new_a != chem["alpha"]:
                chem["alpha"] = new_a
                changed += 1

        self.refresh_table()
        if changed:
            messagebox.showinfo("Alphas Updated", f"Recalculated relative volatilities at T={T} K (ref: {ref or 'auto'}).")
        else:
            messagebox.showinfo("Alphas", "No change (data may be missing for some species — edit α manually).")

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for chem in self.chemicals:
            self.tree.insert("", "end", values=(chem["name"], chem["z"], chem["alpha"]))

        # Sync LK/HK combos
        names = [c["name"] for c in self.chemicals]
        if names:
            vals = names
            self.lk_combo.configure(values=vals)
            self.hk_combo.configure(values=vals)

            # Auto-initialize sensible LK/HK if not set or no longer valid
            if not self.lk_name or self.lk_name not in names:
                self.lk_name = names[0]
            if not self.hk_name or self.hk_name not in names:
                self.hk_name = names[-1]

            self.lk_combo.set(self.lk_name)
            self.hk_combo.set(self.hk_name)
        else:
            self.lk_combo.configure(values=["(add chemicals)"])
            self.hk_combo.configure(values=["(add chemicals)"])
            self.lk_combo.set("(add chemicals)")
            self.hk_combo.set("(add chemicals)")
            self.lk_name = ""
            self.hk_name = ""

        # Update feed composition sum indicator
        if hasattr(self, "z_sum_label"):
            total_z = sum(c.get("z", 0.0) for c in self.chemicals)
            color = "#2E7D32" if abs(total_z - 1.0) < 0.005 else "#C62828"
            self.z_sum_label.configure(text=f"Σ z = {total_z:.4f}", text_color=color)

    def edit_z(self):
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        name = self.tree.item(item, "values")[0]

        new_z = ctk.CTkInputDialog(text=f"New feed fraction (z) for {name}:", title="Edit z").get_input()
        if new_z:
            for chem in self.chemicals:
                if chem["name"] == name:
                    chem["z"] = float(new_z)
                    break
            self.refresh_table()

    def remove_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        name = self.tree.item(selected[0], "values")[0]
        self.chemicals = [c for c in self.chemicals if c["name"] != name]
        self.refresh_table()

    def clear_all(self):
        self.chemicals = []
        self.lk_name = ""
        self.hk_name = ""
        self.refresh_table()
        self.results_box.delete("1.0", "end")

    # --- LK / HK management ---
    def _on_lk_changed(self, choice: str):
        if choice and choice != "(add chemicals)":
            self.lk_name = choice

    def _on_hk_changed(self, choice: str):
        if choice and choice != "(add chemicals)":
            self.hk_name = choice

    def set_selected_as_lk(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select row", "Select a row in the table first.")
            return
        name = self.tree.item(selected[0], "values")[0]
        self.lk_name = name
        if self.lk_combo.get() != name:
            self.lk_combo.set(name)
        # If same as HK, warn user (but allow for now)
        if self.hk_name == name and len(self.chemicals) > 1:
            messagebox.showwarning("Same keys", "LK and HK are the same component. Results may be invalid.")

    def set_selected_as_hk(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select row", "Select a row in the table first.")
            return
        name = self.tree.item(selected[0], "values")[0]
        self.hk_name = name
        if self.hk_combo.get() != name:
            self.hk_combo.set(name)
        if self.lk_name == name and len(self.chemicals) > 1:
            messagebox.showwarning("Same keys", "LK and HK are the same component. Results may be invalid.")

    # edit_alpha method removed per user request (α is auto-calculated)

    # --- Presets / Examples ---
    def load_example(self):
        # Simple common distillation examples (ideal or near-ideal)
        examples = {
            "Benzene-Toluene (classic)": {
                "chems": [
                    {"name": "Benzene", "z": 0.45, "alpha": 2.55, "mw": 78.11, "tc": 562.05, "pc_bar": 48.95, "omega": 0.211},
                    {"name": "Toluene", "z": 0.55, "alpha": 1.0, "mw": 92.14, "tc": 591.75, "pc_bar": 41.08, "omega": 0.264},
                ],
                "lk": "Benzene", "hk": "Toluene",
                "flow": 100.0, "feed_temp": 355, "q": 1.0, "lk_rec": 0.99, "hk_rec": 0.99, "r_ratio": 1.3
            },
            "C3 splitter (propane-propylene)": {
                "chems": [
                    {"name": "Propylene", "z": 0.60, "alpha": 1.15, "mw": 42.08, "tc": 364.9, "pc_bar": 46.0, "omega": 0.140},
                    {"name": "Propane", "z": 0.40, "alpha": 1.0, "mw": 44.10, "tc": 369.8, "pc_bar": 42.48, "omega": 0.152},
                ],
                "lk": "Propylene", "hk": "Propane",
                "flow": 200.0, "feed_temp": 310, "q": 1.0, "lk_rec": 0.99, "hk_rec": 0.985, "r_ratio": 1.5
            },
            "Ethylbenzene / Styrene (hard sep)": {
                "chems": [
                    {"name": "Ethylbenzene", "z": 0.55, "alpha": 1.35, "mw": 106.17, "tc": 617.2, "pc_bar": 36.1, "omega": 0.304},
                    {"name": "Styrene", "z": 0.45, "alpha": 1.0, "mw": 104.15, "tc": 603.0, "pc_bar": 37.5, "omega": 0.297},
                ],
                "lk": "Ethylbenzene", "hk": "Styrene",
                "flow": 80.0, "feed_temp": 380, "q": 0.7, "lk_rec": 0.995, "hk_rec": 0.995, "r_ratio": 1.8
            },
            "i-Pentane / n-Pentane": {
                "chems": [
                    {"name": "Isopentane", "z": 0.35, "alpha": 1.25, "mw": 72.15, "tc": 460.4, "pc_bar": 33.8, "omega": 0.227},
                    {"name": "n-Pentane", "z": 0.65, "alpha": 1.0, "mw": 72.15, "tc": 469.7, "pc_bar": 33.7, "omega": 0.252},
                ],
                "lk": "Isopentane", "hk": "n-Pentane",
                "flow": 150.0, "feed_temp": 340, "q": 1.0, "lk_rec": 0.98, "hk_rec": 0.98, "r_ratio": 1.4
            },
        }

        # For demo, pick one or let user choose via simple dialog simulation
        # Use first as default for one-click; advanced users can add more via search
        choice = "Benzene-Toluene (classic)"
        ex = examples[choice]

        self.chemicals = [c.copy() for c in ex["chems"]]
        self.lk_name = ex["lk"]
        self.hk_name = ex["hk"]

        # Set feed specs too for convenience
        self.feed_flow.delete(0, "end"); self.feed_flow.insert(0, str(ex["flow"]))
        if "feed_temp" in ex:
            self.feed_temp.delete(0, "end"); self.feed_temp.insert(0, str(ex["feed_temp"]))
        # Note: q is no longer user-editable; it is always derived from T_feed + P
        self.lk_rec.delete(0, "end"); self.lk_rec.insert(0, str(ex["lk_rec"]))
        self.hk_rec.delete(0, "end"); self.hk_rec.insert(0, str(ex["hk_rec"]))
        self.r_ratio.delete(0, "end"); self.r_ratio.insert(0, str(ex["r_ratio"]))

        self.refresh_table()
        messagebox.showinfo("Example Loaded", f"Loaded preset: {choice}\nAdjust specs or α as needed then Calculate.")

    # --- New feed temperature → q and normalize features ---
    def normalize_feed(self):
        """Scale all z so they sum exactly to 1.0 (user convenience)."""
        if not self.chemicals:
            return
        total = sum(float(c.get("z", 0.0)) for c in self.chemicals)
        if total < 1e-12:
            messagebox.showwarning("Normalize", "Sum of feed fractions is zero — cannot normalize.")
            return
        for c in self.chemicals:
            c["z"] = round(c["z"] / total, 6)
        self.refresh_table()
        messagebox.showinfo("Normalized", f"Feed composition normalized to sum = 1.0 (was {total:.5f}).")

    # calculate_q_from_feed_temp removed — q is now always derived internally during Calculate

    # --- Feed basis conversion helpers (molar <-> mass) ---
    def _get_mw_dict(self):
        return {c["name"]: c.get("mw", 100.0) for c in self.chemicals}

    def _convert_z_to_moles(self, z_display, comp_basis):
        """Return mole-fraction dict from whatever is currently displayed in the table."""
        mw = self._get_mw_dict()
        names = list(z_display.keys())
        if comp_basis.startswith("Mole"):
            return {n: float(z_display[n]) for n in names}  # already mole frac

        # Mass fraction -> mole fraction
        mass_frac = {n: float(z_display[n]) for n in names}
        moles = {}
        total_moles = 0.0
        for n in names:
            m = mw.get(n, 100.0)
            moles[n] = mass_frac[n] / m if m > 0 else 0.0
            total_moles += moles[n]
        if total_moles < 1e-12:
            return {n: 0.0 for n in names}
        return {n: moles[n] / total_moles for n in names}

    def _get_total_molar_flow(self):
        """Return feed flow in kmol/h regardless of selected basis."""
        try:
            val = float(self.feed_flow.get())
        except:
            val = 100.0
        basis = self.flow_basis.get() if hasattr(self, "flow_basis") else "kmol/h (molar)"
        if "kg" in basis.lower() or "mass" in basis.lower():
            # Need average MW of feed
            mw_dict = self._get_mw_dict()
            z_mole = self._get_current_mole_z()
            if not z_mole:
                return val / 100.0   # fallback
            avg_mw = sum(z_mole.get(n, 0) * mw_dict.get(n, 100) for n in z_mole)
            if avg_mw < 1:
                avg_mw = 100.0
            return val / avg_mw   # kg/h / (kg/kmol) = kmol/h
        else:
            return val   # already kmol/h

    def _get_current_mole_z(self):
        """Return current composition as mole fractions (always)."""
        if not self.chemicals:
            return {}
        z_display = {c["name"]: c["z"] for c in self.chemicals}
        comp_basis = self.comp_basis.get() if hasattr(self, "comp_basis") else "Mole fractions"
        return self._convert_z_to_moles(z_display, comp_basis)

    def on_comp_basis_changed(self, choice=None):
        """Convert displayed z when user changes composition basis."""
        if not self.chemicals or not hasattr(self, "comp_basis"):
            return
        current_basis = self.comp_basis.get()
        # Get current displayed values
        z_old = {c["name"]: c["z"] for c in self.chemicals}
        # Convert to mole
        z_mole = self._convert_z_to_moles(z_old, current_basis)
        mw = self._get_mw_dict()

        # Now convert to the *new* desired display basis? The combobox has already changed.
        # For simplicity we always convert the internal list to the basis the user just chose.
        new_basis = current_basis

        if new_basis.startswith("Mole"):
            for c in self.chemicals:
                c["z"] = round(z_mole.get(c["name"], 0.0), 5)
        else:
            # mole -> mass fraction
            mass = {}
            total_mass = 0.0
            for n in z_mole:
                m = mw.get(n, 100.0)
                mass[n] = z_mole[n] * m
                total_mass += mass[n]
            if total_mass < 1e-12:
                total_mass = 1.0
            for c in self.chemicals:
                c["z"] = round(mass.get(c["name"], 0.0) / total_mass, 5)

        self.refresh_table()

    # --- NRTL support ---


    # ==================== CALCULATION (full new workflow) ====================
    def calculate(self):
        if len(self.chemicals) < 2:
            messagebox.showerror("Error", "Add at least two chemicals.")
            return

        components = [c["name"] for c in self.chemicals]

        # Resolve LK / HK
        lk = self.lk_name or components[0]
        hk = self.hk_name or components[-1]
        if lk == hk and len(components) > 1:
            messagebox.showwarning("Key Selection", "Light Key and Heavy Key are identical. Please select different keys.")
            return
        if lk not in components or hk not in components:
            messagebox.showerror("Error", "Selected LK or HK is not in the current list.")
            return

        try:
            # === READ NEW FEED INPUTS (molar/mass aware) ===
            total_molar_flow = self._get_total_molar_flow()          # always kmol/h
            z_mole = self._get_current_mole_z()                       # always mole fractions

            try:
                T_feed = float(self.feed_temp.get())
            except:
                T_feed = 350.0
            try:
                P_bar = float(self.pressure.get())
            except:
                P_bar = 1.0

            lk_rec_d = float(self.lk_rec.get())
            hk_rec_b = float(self.hk_rec.get())
            r_ratio = float(self.r_ratio.get())

            if not (0 < lk_rec_d <= 1.0) or not (0 < hk_rec_b <= 1.0):
                messagebox.showerror("Spec Error", "Recoveries must be between 0 and 1.")
                return
            if r_ratio < 1.0:
                r_ratio = 1.1
            if total_molar_flow <= 0:
                messagebox.showerror("Error", "Feed flow must be positive.")
                return

            # Build alpha dict from current table
            alpha = {c["name"]: c["alpha"] for c in self.chemicals}



            # === DERIVE q internally using ideal model ===
            q, feed_state, q_info = compute_feed_quality(components, z_mole, T_feed, P_bar)

            # === RUN Fenske-Underwood-Gilliland-Kirkbride on consistent molar basis ===
            calc = FUGKDistillation(
                components=components,
                z_feed=z_mole,
                alpha=alpha,
                feed_flow=total_molar_flow,
                q=q,
                pressure=P_bar,
                lk=lk,
                hk=hk
            )
            results = calc.calculate(
                lk_recovery_d=lk_rec_d,
                hk_recovery_b=hk_rec_b,
                R_over_Rmin=r_ratio
            )

            # === PRODUCT FLOWS (molar) ===
            D_molar = sum(results.component_splits[c][0] for c in components)
            B_molar = sum(results.component_splits[c][1] for c in components)

            # Convert to mass flows
            mw_dict = self._get_mw_dict()
            D_mass = sum(results.component_splits[c][0] * mw_dict.get(c, 100) for c in components)
            B_mass = sum(results.component_splits[c][1] * mw_dict.get(c, 100) for c in components)

            # === THERMODYNAMIC TEMPERATURES (top/bottom) using ideal model ===
            xd = results.distillate_composition
            xb = results.bottoms_composition
            T_top = estimate_dew_point(
                components, [xd.get(c, 0) for c in components], P_bar,
                T_guess=T_feed - 10
            )
            T_bot = estimate_bubble_point(
                components, [xb.get(c, 0) for c in components], P_bar,
                T_guess=T_feed + 30
            )

            # === DUTIES (very approximate shortcut energy balance) ===
            R = results.R_actual
            lambda_top = estimate_average_latent_heat(components, [xd.get(c, 0) for c in components], T_top)

            # Condenser (total condenser assumed)
            Q_c_kW = (D_molar * (R + 1.0) * lambda_top) / 3600.0

            # Rough reboiler
            feed_enthalpy_credit = (1.0 - q) * 0.6 * lambda_top * total_molar_flow
            Q_r_kW = Q_c_kW + (B_molar * 0.15 * lambda_top / 3600.0) - (feed_enthalpy_credit / 3600.0)
            Q_r_kW = max(Q_r_kW, Q_c_kW * 0.7)

            # Apply thermodynamic sign convention:
            # Positive = heat into the system (reboiler)
            # Negative = heat out of the system (condenser)
            Q_condenser = -abs(Q_c_kW)
            Q_reboiler = +abs(Q_r_kW)

            # === COLUMN SIZING ===
            try:
                tray_val = float(self.tray_spacing.get())
            except:
                tray_val = 24.0
            units = self.tray_spacing_units.get() if hasattr(self, "tray_spacing_units") else "inches"
            tray_spacing_m = (tray_val / 1000.0) if "mm" in units.lower() else (tray_val * 0.0254)

            N_act = max(results.N_actual, 2)
            height_m = N_act * tray_spacing_m + 3.0 * tray_spacing_m   # extra space top+bottom + reboiler/condenser

            # Preliminary diameter (very approximate, rectifying section controlling)
            # Vapor volumetric flow at top (rough)
            avg_mw_top = sum(xd.get(c, 0) * mw_dict.get(c, 100) for c in components)
            if avg_mw_top < 1:
                avg_mw_top = 80.0
            # Ideal gas vapor density (kg/m3) at T_top, P
            R_gas = 8314.0  # J/kmol.K
            rho_v = (P_bar * 1e5 * avg_mw_top) / (R_gas * (T_top + 10))   # approx
            if rho_v < 0.05 or rho_v > 100:
                rho_v = 2.5

            V_rect_kmol_h = D_molar * (R + 1.0)
            if rho_v > 0:
                V_rect_m3_s = (V_rect_kmol_h * avg_mw_top / 3600.0) / rho_v   # m3/s
            else:
                V_rect_m3_s = 0.1

            # Allowable velocity (m/s) - simple rule of thumb with density correction
            u_allow = 0.85 * ( (800.0 - rho_v) / rho_v )**0.5 * 0.25   # very rough
            u_allow = max(0.3, min(u_allow, 1.8))

            area = V_rect_m3_s / u_allow if u_allow > 0 else 0.5
            diameter_m = (4.0 * area / 3.1416)**0.5
            diameter_m = max(0.4, min(diameter_m, 8.0))   # sanity

            # === STORE RESULTS (richer) ===
            self.last_results = {
                "inputs": {
                    "components": components,
                    "z_mole": z_mole,
                    "alpha": alpha,
                    "total_molar_feed_kmolh": total_molar_flow,
                    "feed_temp_K": T_feed,
                    "pressure_bar": P_bar,
                    "derived_q": q,
                    "feed_state": feed_state,
                    "lk": lk, "hk": hk,
                    "lk_rec_d": lk_rec_d, "hk_rec_b": hk_rec_b,
                    "r_ratio": r_ratio,
                    "tray_spacing_m": tray_spacing_m,
                },
                "results": results,
                "thermo": {
                    "D_molar": D_molar, "B_molar": B_molar,
                    "D_mass": D_mass, "B_mass": B_mass,
                    "T_top_K": T_top, "T_bot_K": T_bot,
                    "Q_condenser_kW": round(Q_condenser, 2),
                    "Q_reboiler_kW": round(Q_reboiler, 2),
                    "column_height_m": round(height_m, 2),
                    "column_diameter_m": round(diameter_m, 2),
                }
            }

            # === BUILD RICH OUTPUT ===
            self.results_box.delete("1.0", "end")
            lines = []
            lines.append("=== Fenske-Underwood-Gilliland-Kirkbride (FUGK) SHORTCUT DISTILLATION RESULTS (full workflow) ===\n")
            lines.append("⚠️ DISCLAIMER: This tool uses ONLY Raoult's Law (ideal VLE assumption: K_i = P_sat,i(T) / P) for all thermodynamic calculations (feed q, K-values, bubble/dew points, etc.).")
            lines.append("   Results are approximate and should be treated with caution for any real mixture that exhibits non-idealities (azeotropes, activity coefficients ≠ 1, etc.).")
            lines.append("   Always validate with rigorous simulation for final design.\n")
            lines.append(f"LK: {lk}  |  HK: {hk}")
            lines.append(f"Feed: {total_molar_flow:.2f} kmol/h   |   T_feed = {T_feed:.1f} K   |   P = {P_bar:.2f} bar")
            lines.append(f"Derived feed condition: q = {q:.3f}   ({feed_state})")
            lines.append(f"Recoveries: LK→D {lk_rec_d*100:.1f}%   |   HK→B {hk_rec_b*100:.1f}%   |   R/Rmin = {r_ratio:.2f}\n")

            lines.append("--- Fenske-Underwood-Gilliland-Kirkbride (FUGK) Results ---")
            lines.append(f"N_min = {results.N_min}     R_min = {results.R_min}")
            lines.append(f"Actual stages = {results.N_actual}     Operating R = {results.R_actual}")
            lines.append(f"Optimal feed stage at minimum stages (Fenske / total reflux): {results.feed_stage_min}")
            lines.append(f"Optimal feed stage at actual operating stages (Gilliland): {results.feed_stage_actual}\n")

            lines.append("--- Distillate & Bottoms ---")
            lines.append(f"Distillate: {D_molar:.2f} kmol/h   ({D_mass:.1f} kg/h)")
            lines.append(f"Bottoms   : {B_molar:.2f} kmol/h   ({B_mass:.1f} kg/h)")
            lines.append(f"Top temperature (est. dew point)    ≈ {T_top} K")
            lines.append(f"Bottom temperature (est. bubble pt) ≈ {T_bot} K\n")

            lines.append("--- Duties (thermodynamic sign convention) ---")
            lines.append(f"Condenser duty (heat leaving system)  ≈ {Q_condenser:.1f} kW")
            lines.append(f"Reboiler duty (heat entering system)  ≈ {Q_reboiler:.1f} kW")

            if Q_reboiler < 0:
                lines.append("** WARNING: Reboiler duty is negative. **")
                lines.append("This is physically unusual for a standard distillation column (heat is normally added in the reboiler).")
                lines.append("Possible causes: high feed vapor fraction (very low q), excessive operating reflux, or the shortcut energy balance approximation becoming unreliable.")
                lines.append("Review feed temperature, composition, q (derived from your T_feed + P), key recoveries, and R/Rmin. Validate with a rigorous simulator.\n")

            lines.append("--- Column Sizing (preliminary) ---")
            ts_units = "mm" if tray_spacing_m < 0.1 else "in"
            ts_disp = tray_spacing_m * 1000 if ts_units == "mm" else tray_spacing_m / 0.0254
            lines.append(f"Tray spacing (user) = {ts_disp:.1f} {ts_units}")
            lines.append(f"Estimated height (incl. allowances) ≈ {height_m:.1f} m")
            lines.append(f"Estimated diameter (80% flood approx) ≈ {diameter_m:.2f} m\n")

            lines.append("Tray numbering and height basis (important assumptions):")
            lines.append("- Tray #1 = the top tray in the column. The condenser (even a total condenser) is not counted as a tray.")
            lines.append("- The reboiler is treated as the final equilibrium stage. Therefore N_actual includes the reboiler as one of the contact stages.")
            lines.append("- Feed stages (Kirkbride correlation):")
            lines.append("  - feed_stage_min: recommended feed location if the column ran at total reflux (using N_min from Fenske).")
            lines.append("  - feed_stage_actual: recommended feed location for the actual operating column (using N_actual from Gilliland).")
            lines.append("  Both are numbered starting from Tray #1 at the top.")
            lines.append("- Column height calculation = (N_actual) × tray spacing + extra allowance (currently ~3 × tray spacing).")
            lines.append("  The allowance accounts for: top vapor disengagement space, bottom liquid sump / reboiler, condenser, and support.")
            lines.append("- Diameter is a rough estimate based on vapor loading in the rectifying section (highest vapor flow) at ~80% of flooding.")
            lines.append("- These are preliminary shortcut sizing numbers only. Real design needs tray efficiency, downcomer area, weir height, pressure drop per tray, etc.\n")

            if results.warnings:
                lines.append("Warnings: " + " | ".join(results.warnings) + "\n")

            lines.append("Component distribution (kmol/h):")
            lines.append(f"{'Comp':<16} {'z_mole':>8} {'α':>6} {'D':>9} {'B':>9} {'%toD':>7}")
            lines.append("-" * 58)
            for c in components:
                d, b = results.component_splits[c]
                rec = results.component_recoveries[c]
                zm = z_mole.get(c, 0)
                a = alpha.get(c, 1)
                lines.append(f"{c:<16} {zm:8.4f} {a:6.3f} {d:9.2f} {b:9.2f} {rec*100:6.1f}%")
            lines.append("-" * 58)

            lines.append("\nProduct mole fractions:")
            for c in components:
                lines.append(f"  {c:<14} xD={results.distillate_composition[c]:.4f}   xB={results.bottoms_composition[c]:.4f}")

            lines.append("\n(Assumptions: constant α, Raoult's Law / ideal VLE only for all thermo calculations, total condenser, CMO for duties, simple flooding for diameter. This tool is for preliminary/educational use only — validate with rigorous simulator for final design.)")

            self.results_box.insert("1.0", "\n".join(lines))

        except Exception as e:
            import traceback
            messagebox.showerror("Calculation Failed", f"{e}\n\n{traceback.format_exc()[-800:]}")

    # --- Results utilities ---
    def copy_results(self):
        if not self.last_results:
            # fall back to whatever text is shown
            text = self.results_box.get("1.0", "end").strip()
        else:
            # Rebuild a compact text version
            res = self.last_results["results"]
            text = self.results_box.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Copied", "Results copied to clipboard.")
        else:
            messagebox.showinfo("Nothing to copy", "Run a calculation first.")

    def export_csv(self):
        if not self.last_results:
            messagebox.showwarning("No results", "Run a calculation before exporting.")
            return

        res = self.last_results["results"]
        inp = self.last_results["inputs"]

        # Ask user for file (tkinter filedialog)
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="fugk_results.csv"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Fenske-Underwood-Gilliland-Kirkbride (FUGK) Distillation Results Export"])
                w.writerow([])
                w.writerow(["Inputs"])
                w.writerow(["Feed flow (kmol/h)", inp.get("feed_flow")])
                w.writerow(["Feed Temperature (K)", inp.get("feed_temp_K")])
                w.writerow(["q (feed thermal)", inp.get("q")])
                w.writerow(["Pressure (bar)", inp.get("pressure_bar", inp.get("pressure"))])
                w.writerow(["LK", inp["lk"], "Recovery to D", inp["lk_rec_d"]])
                w.writerow(["HK", inp["hk"], "Recovery to B", inp["hk_rec_b"]])
                w.writerow(["R / Rmin", inp["r_ratio"]])
                w.writerow([])
                w.writerow(["Key Results"])
                w.writerow(["N_min", res.N_min])
                w.writerow(["R_min", res.R_min])
                w.writerow(["N_actual", res.N_actual])
                w.writerow(["R_actual", res.R_actual])
                w.writerow(["Feed stage (min stages, total reflux)", res.feed_stage_min])
                w.writerow(["Feed stage (actual operating stages)", res.feed_stage_actual])
                w.writerow([])
                w.writerow(["Component", "z_feed", "alpha", "D_flow_kmolh", "B_flow_kmolh", "rec_to_D", "xD", "xB"])
                for c in inp["components"]:
                    d, b = res.component_splits[c]
                    rec = res.component_recoveries[c]
                    w.writerow([
                        c,
                        round(inp["z_feed"][c], 5),
                        round(inp["alpha"][c], 4),
                        round(d, 4),
                        round(b, 4),
                        round(rec, 5),
                        res.distillate_composition[c],
                        res.bottoms_composition[c]
                    ])
                if res.warnings:
                    w.writerow([])
                    w.writerow(["Warnings"])
                    for ww in res.warnings:
                        w.writerow([ww])
            messagebox.showinfo("Exported", f"Results saved to:\n{path}")
        except Exception as ex:
            messagebox.showerror("Export failed", str(ex))


if __name__ == "__main__":
    app = FUGKApp()
    app.mainloop()