#!/usr/bin/env python3
import os
import threading
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt


# -------------------- Core math --------------------
def capacity_and_cutoff(
    path: str,
    cutoff_v: float = 2.7,
    skiprows: int = 4,
    use_abs_current: bool = True,
    sep: str = r"[\t,;]+",
):
    """
    Columns by position (0-based):
      0 -> Time (s)
      2 -> Voltage (V)
      4 -> Current (A)

    Integrates current while Voltage >= cutoff_v.
    When voltage crosses below cutoff_v between samples, interpolates t_cut and i_cut
    and adds partial trapezoid.
    """
    df = pd.read_csv(
        path,
        sep=sep,
        engine="python",
        skiprows=skiprows,
        header=0,
        usecols=[0, 2, 4],
    )
    df.columns = ["t", "v", "i"]

    df["t"] = pd.to_numeric(df["t"], errors="coerce")
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    df["i"] = pd.to_numeric(df["i"], errors="coerce")
    df = df.dropna(subset=["t", "v", "i"])
    if df.empty:
        raise ValueError("No numeric data found after cleaning (t,v,i).")

    t = df["t"].to_numpy(dtype=np.float64)
    v = df["v"].to_numpy(dtype=np.float64)
    i = df["i"].to_numpy(dtype=np.float64)

    if use_abs_current:
        i = np.abs(i)

    # Find first point where v < cutoff (we count while v >= cutoff)
    below = v < cutoff_v
    if below.any():
        idx = int(np.where(below)[0][0])
        if idx == 0:
            coulomb = 0.0
            t_cut = float(t[0])
            rows_used = 0
            reached = True
        else:
            t_prev, t_cur = t[idx - 1], t[idx]
            v_prev, v_cur = v[idx - 1], v[idx]
            i_prev, i_cur = i[idx - 1], i[idx]

            if v_cur == v_prev:
                # flat voltage; treat cutoff at current sample
                t_cut = float(t[idx])
                coulomb = np.trapz(i[: idx + 1], t[: idx + 1])
                rows_used = idx + 1
            else:
                frac = (cutoff_v - v_prev) / (v_cur - v_prev)
                frac = max(0.0, min(1.0, frac))
                t_cut = t_prev + frac * (t_cur - t_prev)
                i_cut = i_prev + frac * (i_cur - i_prev)

                # integrate full trapezoids up to t_prev
                if idx >= 2:
                    coulomb = np.trapz(i[:idx], t[:idx])
                else:
                    coulomb = 0.0

                # add partial trapezoid from t_prev to t_cut
                coulomb += 0.5 * (i_prev + i_cut) * (t_cut - t_prev)
                rows_used = idx
            reached = True
    else:
        coulomb = np.trapz(i, t)
        t_cut = float(t[-1])
        rows_used = len(t)
        reached = False

    ah = coulomb / 3600.0
    mah = ah * 1000.0

    return {
        "t": t,
        "v": v,
        "i": i,
        "ah": float(ah),
        "mah": float(mah),
        "t_cut": float(t_cut),
        "rows_used": int(rows_used),
        "reached": bool(reached),
    }


def downsample_for_plot(x, y, max_points=200_000):
    n = x.shape[0]
    if n <= max_points:
        return x, y
    stride = int(np.ceil(n / max_points))
    return x[::stride], y[::stride]


def plot_and_save(data, cutoff_v: float, out_png: str, show: bool = True):
    """
    IMPORTANT: Must be called from the main thread (Tkinter main loop).
    """
    t = data["t"]
    v = data["v"]
    i = data["i"]
    t_cut = data["t_cut"]

    mask = t <= t_cut
    t_plot = t[mask]
    v_plot = v[mask]
    i_plot = i[mask]

    t_i, i_ds = downsample_for_plot(t_plot, i_plot)
    t_v, v_ds = downsample_for_plot(t_plot, v_plot)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    ax1, ax2 = axes

    ax1.plot(t_i, i_ds, linewidth=0.6, label="Current (A)")
    ax1.axvline(t_cut, color="red", linestyle="--", label=f"Cutoff @ {t_cut:.3f}s")
    ax1.set_ylabel("Current (A)")
    ax1.grid(True)
    ax1.legend(loc="best")

    ax2.plot(t_v, v_ds, linewidth=0.6, label="Voltage (V)")
    ax2.axhline(cutoff_v, color="orange", linestyle="--", label=f"Cutoff V = {cutoff_v} V")
    ax2.axvline(t_cut, color="red", linestyle="--")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Voltage (V)")
    ax2.grid(True)
    ax2.legend(loc="best")

    fig.suptitle(f"Capacity until V < {cutoff_v} V: {data['mah']:.3f} mAh  (cutoff {t_cut:.3f} s)")
    fig.tight_layout(rect=[0, 0.03, 1, 0.97])

    fig.savefig(out_png, dpi=150)

    if show:
        plt.show()
    else:
        plt.close(fig)


# -------------------- GUI --------------------
class CapacityGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Battery Capacity (to Voltage Cutoff)")
        self.geometry("740x340")

        self.csv_path_var = tk.StringVar()
        self.cutoff_var = tk.StringVar(value="2.7")
        self.batt_id_var = tk.StringVar()
        self.abs_current_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # CSV row
        frm1 = tk.Frame(self)
        frm1.pack(fill="x", **pad)
        tk.Label(frm1, text="CSV file:").pack(side="left")
        tk.Entry(frm1, textvariable=self.csv_path_var, width=74).pack(side="left", padx=8)
        tk.Button(frm1, text="Browse...", command=self.on_browse).pack(side="left")

        # Cutoff row
        frm2 = tk.Frame(self)
        frm2.pack(fill="x", **pad)
        tk.Label(frm2, text="Cutoff voltage (V):").pack(side="left")
        tk.Entry(frm2, textvariable=self.cutoff_var, width=10).pack(side="left", padx=8)

        # Battery ID row
        frm3 = tk.Frame(self)
        frm3.pack(fill="x", **pad)
        tk.Label(frm3, text="Battery ID:").pack(side="left")
        tk.Entry(frm3, textvariable=self.batt_id_var, width=30).pack(side="left", padx=8)
        tk.Label(frm3, text="(default = filename)").pack(side="left")

        # Options row
        frm4 = tk.Frame(self)
        frm4.pack(fill="x", **pad)
        tk.Checkbutton(frm4, text="Use abs(current) for integration", variable=self.abs_current_var).pack(side="left")

        # Buttons
        frm5 = tk.Frame(self)
        frm5.pack(fill="x", **pad)
        self.run_btn = tk.Button(frm5, text="Run", command=self.on_run)
        self.run_btn.pack(side="left")
        tk.Button(frm5, text="Quit", command=self.destroy).pack(side="left", padx=10)

        # Output text
        frm6 = tk.Frame(self)
        frm6.pack(fill="both", expand=True, **pad)
        tk.Label(frm6, text="Result:").pack(anchor="w")
        self.out = tk.Text(frm6, height=8, wrap="word")
        self.out.pack(fill="both", expand=True)

    def on_browse(self):
        path = filedialog.askopenfilename(
            title="Select CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.csv_path_var.set(path)

        # default battery ID from filename (only if empty)
        base = os.path.splitext(os.path.basename(path))[0]
        if not self.batt_id_var.get().strip():
            self.batt_id_var.set(base)

    def _append_out(self, text: str):
        self.out.insert("end", text + "\n")
        self.out.see("end")

    def on_run(self):
        path = self.csv_path_var.get().strip()
        if not path:
            messagebox.showerror("Error", "Please select a CSV file.")
            return
        if not os.path.isfile(path):
            messagebox.showerror("Error", "Selected file does not exist.")
            return

        try:
            cutoff = float(self.cutoff_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Cutoff voltage must be a number.")
            return

        batt_id = self.batt_id_var.get().strip()
        if not batt_id:
            batt_id = os.path.splitext(os.path.basename(path))[0]
            self.batt_id_var.set(batt_id)

        self.run_btn.config(state="disabled")
        self.out.delete("1.0", "end")
        self._append_out("Running... (reading file and computing)")

        # Run compute in background (no GUI calls there)
        th = threading.Thread(target=self._compute_in_thread, args=(path, cutoff, batt_id), daemon=True)
        th.start()

    def _compute_in_thread(self, path: str, cutoff: float, batt_id: str):
        try:
            data = capacity_and_cutoff(
                path,
                cutoff_v=cutoff,
                skiprows=4,
                use_abs_current=self.abs_current_var.get(),
                sep=r"[\t,;]+",  # robust for comma/tab/semicolon
            )

            out_dir = os.path.dirname(path)
            out_png = os.path.join(out_dir, f"{batt_id}_I_V_plot.png")

            # Return to main thread: update UI + plot (matplotlib) safely
            def ui_update_and_plot():
                self._append_out(f"File: {path}")
                self._append_out(f"Battery ID: {batt_id}")
                self._append_out(f"Cutoff reached: {data['reached']}")
                self._append_out(f"Cutoff voltage: {cutoff:.4f} V")
                self._append_out(f"Cutoff time: {data['t_cut']:.6f} s")
                self._append_out(f"Rows used: {data['rows_used']}")
                self._append_out(f"Capacity: {data['ah']:.9f} Ah")
                self._append_out(f"Capacity: {data['mah']:.6f} mAh")
                self._append_out(f"Plot saved: {out_png}")
                self.run_btn.config(state="normal")

                # Plot in main thread
                plot_and_save(data, cutoff_v=cutoff, out_png=out_png, show=True)

            self.after(0, ui_update_and_plot)

        except Exception as e:
            def ui_err():
                self._append_out(f"ERROR: {e}")
                self.run_btn.config(state="normal")
                messagebox.showerror("Error", str(e))
            self.after(0, ui_err)


if __name__ == "__main__":
    app = CapacityGUI()
    app.mainloop()
