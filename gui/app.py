"""
CustomTkinter GUI for FUGK Shortcut Distillation Calculator
Designed for easy .exe distribution (Windows + macOS)
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.fug import FUGKDistillation
from core.chemical_database import search_chemicals, calculate_relative_volatility

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class FUGKApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FUGK Distillation Calculator")
        self.geometry("1100x750")
        self.minsize(1000, 650)

        self.components_vars = []
        self.z_vars = []
        self.alpha_vars = []

        self.create_widgets()

    def create_widgets(self):
        title_frame = ctk.CTkFrame(self)
        title_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(title_frame, text="🧪 FUGK Shortcut Distillation Calculator",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=5)
        ctk.CTkLabel(title_frame, text="Reverse-engineered Aspen DSTWU | Fenske-Underwood-Gilliland-Kirkbride",
                     font=ctk.CTkFont(size=12)).pack()

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        left_frame = ctk.CTkFrame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # === LEFT COLUMN ===
        ctk.CTkLabel(left_frame, text="1. System Definition",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5), anchor="w", padx=10)

        num_frame = ctk.CTkFrame(left_frame)
        num_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(num_frame, text="Number of Components:").pack(side="left", padx=5)
        self.num_comp_spin = ctk.CTkEntry(num_frame, width=60)
        self.num_comp_spin.insert(0, "3")
        self.num_comp_spin.pack(side="left", padx=5)
        ctk.CTkButton(num_frame, text="Update Components", command=self.update_components).pack(side="left", padx=10)

        self.comp_frame = ctk.CTkFrame(left_frame)
        self.comp_frame.pack(fill="x", padx=10, pady=5)
        self.update_components()

        # Chemical Search Section
        ctk.CTkLabel(left_frame, text="Chemical Search (real data)",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5), anchor="w", padx=10)

        search_frame = ctk.CTkFrame(left_frame)
        search_frame.pack(fill="x", padx=10, pady=5)

        self.search_var = ctk.CTkEntry(search_frame, width=200, placeholder_text="e.g. benzene, toluene, acetone")
        self.search_var.pack(side="left", padx=5)

        ctk.CTkButton(search_frame, text="Search", width=70, command=self.search_chemical).pack(side="left", padx=5)

        self.search_results = ctk.CTkComboBox(search_frame, width=250, values=["Search results will appear here"])
        self.search_results.pack(side="left", padx=5)

        temp_frame = ctk.CTkFrame(left_frame)
        temp_frame.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(temp_frame, text="Temperature for α (K):").pack(side="left", padx=5)
        self.temp_var = ctk.CTkEntry(temp_frame, width=80)
        self.temp_var.insert(0, "353.15")
        self.temp_var.pack(side="left", padx=5)

        ctk.CTkButton(left_frame, text="➕ Add Selected Chemical + Calculated α",
                      command=self.add_selected_chemical).pack(pady=5, padx=10, fill="x")

        # Feed conditions
        ctk.CTkLabel(left_frame, text="Feed Conditions",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5), anchor="w", padx=10)

        feed_frame = ctk.CTkFrame(left_frame)
        feed_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(feed_frame, text="Feed Flow (kmol/h):").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.feed_flow_var = ctk.CTkEntry(feed_frame, width=100)
        self.feed_flow_var.insert(0, "100")
        self.feed_flow_var.grid(row=0, column=1, padx=5, pady=3)

        ctk.CTkLabel(feed_frame, text="Feed Quality q:").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self.q_var = ctk.CTkEntry(feed_frame, width=100)
        self.q_var.insert(0, "1.0")
        self.q_var.grid(row=1, column=1, padx=5, pady=3)

        ctk.CTkLabel(feed_frame, text="Pressure (bar):").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self.pressure_var = ctk.CTkEntry(feed_frame, width=100)
        self.pressure_var.insert(0, "1.0")
        self.pressure_var.grid(row=2, column=1, padx=5, pady=3)

        # Key Components
        ctk.CTkLabel(left_frame, text="Key Components",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5), anchor="w", padx=10)

        key_frame = ctk.CTkFrame(left_frame)
        key_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(key_frame, text="Light Key (LK):").grid(row=0, column=0, sticky="w", padx=5)
        self.lk_var = ctk.CTkEntry(key_frame, width=120)
        self.lk_var.insert(0, "Benzene")
        self.lk_var.grid(row=0, column=1, padx=5)

        ctk.CTkLabel(key_frame, text="Heavy Key (HK):").grid(row=1, column=0, sticky="w", padx=5)
        self.hk_var = ctk.CTkEntry(key_frame, width=120)
        self.hk_var.insert(0, "Toluene")
        self.hk_var.grid(row=1, column=1, padx=5)

        # Specifications
        ctk.CTkLabel(left_frame, text="2. Design Specifications",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 5), anchor="w", padx=10)

        spec_frame = ctk.CTkFrame(left_frame)
        spec_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(spec_frame, text="LK Recovery in Distillate:").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.lk_rec_var = ctk.CTkEntry(spec_frame, width=80)
        self.lk_rec_var.insert(0, "0.99")
        self.lk_rec_var.grid(row=0, column=1, padx=5)

        ctk.CTkLabel(spec_frame, text="HK Recovery in Bottoms:").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self.hk_rec_var = ctk.CTkEntry(spec_frame, width=80)
        self.hk_rec_var.insert(0, "0.99")
        self.hk_rec_var.grid(row=1, column=1, padx=5)

        ctk.CTkLabel(spec_frame, text="R / R_min:").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self.r_ratio_var = ctk.CTkEntry(spec_frame, width=80)
        self.r_ratio_var.insert(0, "1.3")
        self.r_ratio_var.grid(row=2, column=1, padx=5)

        calc_btn = ctk.CTkButton(left_frame, text="🚀 Calculate (FUGK)",
                                 command=self.run_calculation,
                                 font=ctk.CTkFont(size=16, weight="bold"),
                                 height=45)
        calc_btn.pack(pady=20, padx=10, fill="x")

        # === RIGHT COLUMN ===
        ctk.CTkLabel(right_frame, text="Results",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))

        metrics_frame = ctk.CTkFrame(right_frame)
        metrics_frame.pack(fill="x", padx=10, pady=5)

        self.nmin_label = ctk.CTkLabel(metrics_frame, text="N_min: —", font=ctk.CTkFont(size=14))
        self.nmin_label.pack(pady=2)
        self.rmin_label = ctk.CTkLabel(metrics_frame, text="R_min: —", font=ctk.CTkFont(size=14))
        self.rmin_label.pack(pady=2)
        self.nact_label = ctk.CTkLabel(metrics_frame, text="Actual Stages (N): —", font=ctk.CTkFont(size=14, weight="bold"))
        self.nact_label.pack(pady=2)
        self.ract_label = ctk.CTkLabel(metrics_frame, text="Operating Reflux (R): —", font=ctk.CTkFont(size=14, weight="bold"))
        self.ract_label.pack(pady=2)
        self.feed_stage_label = ctk.CTkLabel(metrics_frame, text="Feed Stage: —", font=ctk.CTkFont(size=14))
        self.feed_stage_label.pack(pady=2)

        ctk.CTkLabel(right_frame, text="Component Distribution",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(10, 3))

        self.tree = ttk.Treeview(right_frame, columns=("Feed", "Distillate", "Bottoms", "Rec to D", "Alpha"),
                                 show="headings", height=10)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        for col in ("Feed", "Distillate", "Bottoms", "Rec to D", "Alpha"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=90, anchor="center")

        self.interp_text = ctk.CTkTextbox(right_frame, height=80, wrap="word")
        self.interp_text.pack(fill="x", padx=10, pady=5)
        self.interp_text.insert("1.0", "Run a calculation to see results here.")

        footer = ctk.CTkLabel(self, text="FUGK Calculator • Uses real chemical data where possible",
                              font=ctk.CTkFont(size=10))
        footer.pack(pady=5)

    def search_chemical(self):
        query = self.search_var.get().strip()
        if not query:
            return
        try:
            results = search_chemicals(query, limit=15)
            names = [r["name"] for r in results]
            self.search_results.configure(values=names)
            if names:
                self.search_results.set(names[0])
        except Exception as e:
            messagebox.showerror("Search Error", str(e))

    def add_selected_chemical(self):
        selected = self.search_results.get()
        if not selected or "Search results" in selected:
            messagebox.showwarning("No Selection", "Please search and select a chemical.")
            return

        try:
            T = float(self.temp_var.get())
        except:
            T = 353.15

        current = [v.get().strip() for v in self.components_vars if v.get().strip()]
        ref = current[-1] if current else None
        alpha = calculate_relative_volatility(selected, ref, T) if ref else 1.0

        n = len(self.components_vars)
        if n < 10:
            self.num_comp_spin.delete(0, "end")
            self.num_comp_spin.insert(0, str(n + 1))
            self.update_components()

            self.components_vars[-1].delete(0, "end")
            self.components_vars[-1].insert(0, selected)

            self.alpha_vars[-1].delete(0, "end")
            self.alpha_vars[-1].insert(0, f"{alpha:.3f}" if alpha else "1.0")

            messagebox.showinfo("Added", f"Added {selected} with α ≈ {alpha:.3f}")
        else:
            messagebox.showwarning("Limit", "Max 10 components.")

    def update_components(self):
        for widget in self.comp_frame.winfo_children():
            widget.destroy()

        try:
            n = int(self.num_comp_spin.get())
        except:
            n = 3

        self.components_vars = []
        self.z_vars = []
        self.alpha_vars = []

        headers = ["Component", "z (Feed frac)", "α (rel. volatility)"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.comp_frame, text=h, font=ctk.CTkFont(weight="bold")).grid(row=0, column=i, padx=5, pady=2)

        default_names = ["Benzene", "Toluene", "p-Xylene"]
        default_alphas = [2.5, 1.0, 0.45]

        for i in range(n):
            name_var = ctk.CTkEntry(self.comp_frame, width=110)
            name_var.insert(0, default_names[i] if i < len(default_names) else f"Comp{i+1}")
            name_var.grid(row=i+1, column=0, padx=5, pady=2)
            self.components_vars.append(name_var)

            z_var = ctk.CTkEntry(self.comp_frame, width=80)
            default_z = 0.4 if i == 0 else (0.35 if i == 1 else 0.25)
            z_var.insert(0, f"{default_z:.2f}")
            z_var.grid(row=i+1, column=1, padx=5, pady=2)
            self.z_vars.append(z_var)

            alpha_var = ctk.CTkEntry(self.comp_frame, width=80)
            alpha_var.insert(0, str(default_alphas[i] if i < len(default_alphas) else "1.0"))
            alpha_var.grid(row=i+1, column=2, padx=5, pady=2)
            self.alpha_vars.append(alpha_var)

    def run_calculation(self):
        try:
            components = [v.get().strip() for v in self.components_vars]
            z_feed = {comp: float(self.z_vars[i].get()) for i, comp in enumerate(components)}
            alpha = {comp: float(self.alpha_vars[i].get()) for i, comp in enumerate(components)}

            feed_flow = float(self.feed_flow_var.get())
            q = float(self.q_var.get())
            pressure = float(self.pressure_var.get())

            lk = self.lk_var.get().strip()
            hk = self.hk_var.get().strip()

            lk_recovery = float(self.lk_rec_var.get())
            hk_recovery = float(self.hk_rec_var.get())
            r_ratio = float(self.r_ratio_var.get())

            calc = FUGKDistillation(
                components=components,
                z_feed=z_feed,
                alpha=alpha,
                feed_flow=feed_flow,
                q=q,
                pressure=pressure,
                lk=lk,
                hk=hk
            )

            results = calc.calculate(
                lk_recovery_d=lk_recovery,
                hk_recovery_b=hk_recovery,
                R_over_Rmin=r_ratio
            )

            self.nmin_label.configure(text=f"N_min: {results.N_min}")
            self.rmin_label.configure(text=f"R_min: {results.R_min}")
            self.nact_label.configure(text=f"Actual Stages (N): {results.N_actual}")
            self.ract_label.configure(text=f"Operating Reflux (R): {results.R_actual}")
            self.feed_stage_label.configure(text=f"Recommended Feed Stage: {results.feed_stage}")

            for item in self.tree.get_children():
                self.tree.delete(item)

            for comp in components:
                d_flow, b_flow = results.component_splits[comp]
                rec = results.component_recoveries[comp]
                self.tree.insert("", "end", values=(
                    f"{z_feed[comp]*feed_flow:.2f}",
                    f"{d_flow:.2f}",
                    f"{b_flow:.2f}",
                    f"{rec*100:.1f}%",
                    f"{alpha[comp]:.2f}"
                ))

            self.interp_text.delete("1.0", "end")
            interp = (f"This column requires approximately {results.N_actual:.0f} theoretical stages "
                      f"with an operating reflux of {results.R_actual:.2f}. "
                      f"Feed should enter around stage {results.feed_stage}.")
            self.interp_text.insert("1.0", interp)

        except Exception as e:
            messagebox.showerror("Calculation Error", str(e))


if __name__ == "__main__":
    app = FUGKApp()
    app.mainloop()