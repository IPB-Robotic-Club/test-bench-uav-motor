import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Konstanta konfigurasi
MAX_POINTS_PER_TRIAL = 100
colors = ['red', 'blue', 'green', 'orange', 'purple', 'cyan']
markers = ['o', '^', 's', 'D', 'x', 'v']

# Buffer untuk menyimpan data per label percobaan
trial_buffers = {}

# Buat objek Figure dan Axis global
fig = Figure(figsize=(6, 4))
ax = fig.add_subplot(111)

def setup_embedded_plot(root):
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True)
    return canvas

def update_embedded_plot(data, label):
    # Validasi data masuk
    if not isinstance(data, dict) or "pwm" not in data or "gram" not in data:
        print("⚠️ Data tidak valid untuk plotting:", data)
        return

    # Inisialisasi buffer jika label baru
    if label not in trial_buffers:
        trial_buffers[label] = {"pwm": [], "gram": []}

    buf = trial_buffers[label]
    buf["pwm"].append(data["pwm"])
    buf["gram"].append(data["gram"])

    # Batasi jumlah titik agar tidak overload
    if len(buf["pwm"]) > MAX_POINTS_PER_TRIAL:
        buf["pwm"].pop(0)
        buf["gram"].pop(0)

    # Plot ulang semua trial
    redraw_all()

def redraw_all():
    ax.clear()
    for i, (trial_name, buffer) in enumerate(trial_buffers.items()):
        color = colors[i % len(colors)]
        marker = markers[i % len(markers)]
        ax.plot(buffer["pwm"], buffer["gram"],
                label=trial_name,
                marker=marker,
                color=color,
                linestyle='-')
    ax.set_xlabel("PWM (%)")
    ax.set_ylabel("Thrust (gram)")
    ax.set_title("Thrust vs PWM – Multiple Trials")
    ax.grid(True)
    ax.legend()
    fig.canvas.draw()

def reset_trial(label):
    if label in trial_buffers:
        trial_buffers[label]["pwm"].clear()
        trial_buffers[label]["gram"].clear()
        redraw_all()

def reset_all_trials():
    trial_buffers.clear()
    redraw_all()

# Ekspor fungsi dan variabel agar bisa diakses dari modul lain
__all__ = [
    "setup_embedded_plot",
    "update_embedded_plot",
    "reset_trial",
    "reset_all_trials",
    "trial_buffers",
    "fig",
    "ax"
]