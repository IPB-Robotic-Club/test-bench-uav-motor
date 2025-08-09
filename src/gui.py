import tkinter as tk
import pandas as pd
import json
import time
import os
from tkinter import filedialog, messagebox, ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from src.serial_utils import get_available_ports
from src.serial_handler import open_serial
from PyQt5.QtWidgets import QPushButton

class ThrustTestApp:
    def __init__(self, root):
        self.root = root
        self.selected_mode = None
        self.root.title("Thrust vs PWM Monitor")
        self.manual_data = []
        self.running = False
        self.ser = None

        # Buat PanedWindow vertikal
        paned = ttk.PanedWindow(root, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Frame atas untuk plot
        plot_frame = ttk.Frame(paned)
        paned.add(plot_frame, weight=3)

        # Frame bawah untuk kontrol
        control_frame = ttk.Frame(paned)
        paned.add(control_frame, weight=1)

        # Setup plot
        self.fig = Figure(figsize=(8, 6))
        self.ax = self.fig.add_subplot(111)
        self.setup_plot()

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Frame mode operasi
        mode_frame = tk.Frame(control_frame)
        mode_frame.pack(pady=5)
        tk.Label(mode_frame, text="Pilih Mode Operasi:").pack(side=tk.LEFT)
        tk.Button(mode_frame, text="REAL", bg="lightgreen", command=self.set_real_mode).pack(side=tk.LEFT, padx=5)
        tk.Button(mode_frame, text="DUMMY", bg="lightgray", command=self.set_dummy_mode).pack(side=tk.LEFT, padx=5)

        # Label status mode aktif
        self.mode_status = tk.StringVar(value="Mode: DUMMY")
        tk.Label(control_frame, textvariable=self.mode_status, fg="blue").pack(pady=5)

        # Frame pemilihan port
        port_frame = tk.Frame(control_frame)
        port_frame.pack(pady=5)
        tk.Label(port_frame, text="Pilih COM Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value=get_available_ports()[0] if get_available_ports() else '')
        self.port_menu = tk.OptionMenu(port_frame, self.port_var, *get_available_ports())
        self.port_menu.pack(side=tk.LEFT, padx=5)

        # Frame label percobaan
        label_frame = tk.Frame(control_frame)
        label_frame.pack(pady=5)
        tk.Label(label_frame, text="Label Percobaan:").pack(side=tk.LEFT)
        self.label_var = tk.StringVar(value="Percobaan 1")
        tk.Entry(label_frame, textvariable=self.label_var).pack(side=tk.LEFT, padx=5)

        # Frame override
        override_frame = tk.Frame(control_frame)
        override_frame.pack(pady=5)
        self.override_var = tk.BooleanVar(value=False)
        tk.Checkbutton(override_frame,
                    text="Override pengujian sebelumnya",
                    variable=self.override_var).pack(side=tk.LEFT)

        # Frame tombol kontrol
        button_frame = tk.Frame(control_frame)
        button_frame.pack(pady=5)

        self.all_trials = {}
        self.current_trial = None

        buttons = [
            ("Mulai", "green", "white", self.start_test),
            ("Stop", "red", "white", self.stop_test),
            ("Reset Percobaan", "orange", "black", self.reset_trial),
            ("Simpan Gambar", "blue", "white", self.save_plot),
            ("Simpan Data CSV", "purple", "white", self.save_data),
            ("Kalibrasi Zero", "gray", "white", self.send_calibrate_command)  # ← Tambahkan di sini
        ]

        for (text, bg, fg, command) in buttons:
            btn = tk.Button(button_frame, text=text, command=command,
                            bg=bg, fg=fg, width=15)
            btn.pack(side=tk.LEFT, padx=5)

        # Frame log area
        log_frame = tk.Frame(control_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.log_area = tk.Text(log_frame, height=6, state='disabled', wrap='word')
        self.log_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(log_frame, command=self.log_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_area.config(yscrollcommand=scrollbar.set)

    def log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        print(message)

    def setup_plot(self):
        """Setup awal plot"""
        self.ax.clear()
        self.ax.set_xlabel("PWM (%)")
        self.ax.set_ylabel("Thrust (gram)")
        self.ax.grid(True)
        self.ax.set_title("Grafik Thrust vs PWM")
        self.ax.set_xlim([-5, 105])  # Set batasan PWM
        self.fig.canvas.draw()

    def send_calibrate_command(self):
        if not self.ensure_serial_connected():
            return
        try:
            self.ser.write(b'CALIBRATE_ZERO\n')
            self.log("📤 Perintah kalibrasi dikirim.")
        except Exception as e:
            self.log(f"❌ Gagal kirim perintah: {str(e)}")

    def start_test(self):
        """Memulai pengujian dan komunikasi serial"""
        try:
            current_label = self.label_var.get().strip()
            if not current_label:
                messagebox.showerror("Error", "Label percobaan tidak boleh kosong!")
                return
            
            if not self.override_var.get() and current_label in self.all_trials:
                messagebox.showerror("Error", "Label percobaan sudah digunakan! Gunakan label berbeda atau aktifkan mode override.")
                return
            
            port = self.port_var.get()
            if not port:
                messagebox.showerror("Error", "Pilih COM Port terlebih dahulu!")
                return

            # Stop pengujian sebelumnya jika ada
            if self.running:
                self.stop_test()

            # Set current trial
            self.current_trial = current_label
            
            # Reset data untuk pengujian baru
            self.manual_data = []

            # Pastikan koneksi serial aktif
            if not self.ensure_serial_connected():
                return

            self.running = True

            # 🔧 Kirim mode operasi ke firmware sebelum START
            if self.selected_mode:
                self.ser.write(f"{self.selected_mode}\n".encode())
                print(f"✓ Mode {self.selected_mode} dikirim ke ESP")
            else:
                messagebox.showwarning("Warning", "Pilih mode dulu sebelum mulai!")
                return

            # Kirim perintah ke firmware
            self.ser.write(b"START\n")
            print(f"✓ Memulai pengujian '{current_label}' pada {port}")
            
            self.read_serial()
            
        except Exception as e:
            messagebox.showerror("Error", f"Gagal memulai pengujian: {str(e)}")
            self.stop_test()

    def ensure_serial_connected(self):
        """Memastikan koneksi serial aktif dan siap digunakan"""
        port = self.port_var.get()
        if not port:
            self.log("⚠️ Port belum dipilih.")
            return False

        # Jika sudah terhubung dan port sama, tidak perlu buka ulang
        if self.ser and self.ser.is_open:
            if self.ser.port == port:
                self.log(f"🔄 Serial sudah terhubung ke {port}")
                return True
            else:
                # Port berbeda, tutup koneksi lama
                try:
                    self.ser.close()
                    self.log(f"🔌 Serial lama ({self.ser.port}) ditutup.")
                except Exception as e:
                    self.log(f"❌ Gagal menutup koneksi lama: {str(e)}")

        # Buka koneksi baru
        try:
            self.ser = open_serial(port)
            self.log(f"✅ Serial dibuka di {port}")
            return True
        except Exception as e:
            self.log(f"❌ Gagal membuka serial: {str(e)}")
            return False
            
    def stop_test(self):
        """Menghentikan pengujian dan menutup port serial"""
        if self.ser:
            try:
                self.ser.write(b"STOP\n")
                time.sleep(0.1)
                self.ser.close()
                
                # Simpan data ke dictionary trials
                if self.manual_data and self.current_trial:
                    self.all_trials[self.current_trial] = self.manual_data.copy()
                    print(f"✓ Data percobaan '{self.current_trial}' tersimpan")
                
            except Exception as e:
                print(f"Warning: {str(e)}")
            finally:
                self.ser = None
                
        self.running = False
        time.sleep(1)  # Tunggu port benar-benar tertutup
        print("✓ Pengujian dihentikan")

    def set_real_mode(self):
        self.selected_mode = "REAL"
        self.mode_status.set("Mode: REAL")
        print("✓ Mode REAL dipilih")

    def set_dummy_mode(self):
        self.selected_mode = "DUMMY"
        self.mode_status.set("Mode: DUMMY")
        print("✓ Mode DUMMY dipilih")

    def read_serial(self):
        """Membaca data dari serial dan update plot"""
        if not self.running:
            return

        try:
            if self.ser and self.ser.in_waiting:
                raw_data = self.ser.readline()
                decoded = raw_data.decode().strip()

                # Filter pesan boot ESP32
                if any(boot_msg in decoded for boot_msg in [
                    "POWERON_RESET", "SPI_FAST_FLASH_BOOT",
                    "configsip", "clk_drv", "mode:DIO",
                    "load:0x", "entry 0x"
                ]):
                    return

                # Hanya proses jika format JSON
                if decoded.startswith("{") and decoded.endswith("}"):
                    try:
                        data = json.loads(decoded)

                        if "pwm" in data and "gram" in data:
                            if 0 <= data["pwm"] <= 100 and data["gram"] >= 0:
                                self.manual_data.append(data)

                                # Update plot
                                self.ax.clear()

                                # Plot data dari percobaan sebelumnya
                                colors = ['orange', 'blue', 'green', 'red', 'purple']
                                color_idx = 0

                                for label, trial_data in self.all_trials.items():
                                    if label != self.current_trial:
                                        sorted_trial = sorted(trial_data, key=lambda x: x["pwm"])
                                        pwm_data = [d["pwm"] for d in sorted_trial]
                                        gram_data = [d["gram"] for d in sorted_trial]
                                        self.ax.plot(pwm_data, gram_data, '.-',
                                                    color=colors[color_idx % len(colors)],
                                                    label=label)
                                        color_idx += 1

                                # Plot current data
                                sorted_data = sorted(self.manual_data, key=lambda x: x["pwm"])
                                pwm_data = [d["pwm"] for d in sorted_data]
                                gram_data = [d["gram"] for d in sorted_data]

                                self.ax.plot(pwm_data, gram_data, '.-',
                                            color=colors[color_idx % len(colors)],
                                            label=f"{self.label_var.get()} (current)")

                                # Set axis dan labels
                                self.ax.set_xlim([-5, 105])
                                all_gram_data = gram_data[:]
                                for trial_data in self.all_trials.values():
                                    all_gram_data.extend([d["gram"] for d in trial_data])
                                max_gram = max(all_gram_data) if all_gram_data else 100
                                self.ax.set_ylim([-5, max_gram + 10])

                                self.ax.set_xlabel("PWM (%)")
                                self.ax.set_ylabel("Thrust (gram)")
                                self.ax.grid(True)
                                self.ax.legend()
                                self.canvas.draw()

                                print(f"Data: PWM={data['pwm']}%, Thrust={data['gram']}g")
                            else:
                                print(f"⚠️ Data invalid: PWM={data['pwm']}, Thrust={data['gram']}")
                    except json.JSONDecodeError:
                        print(f"⚠️ JSON tidak valid: {decoded}")
                else:
                    # Tangani pesan status non-JSON
                    print(f"ℹ️ Pesan status: {decoded}")

                    # Tangani hasil kalibrasi dari firmware
                    if decoded.startswith("STATUS:ZERO_CALIBRATED_"):
                        offset = decoded.split("_")[1]
                        self.log(f"✅ Kalibrasi selesai. Offset: {offset}")
                        # Optional: simpan offset ke variabel
                        self.zero_offset = int(offset)
                        # Optional: tampilkan di label GUI jika ada
                        # self.label_offset.setText(f"Offset: {self.zero_offset}")

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.stop_test()
            return

        if self.running:
            self.root.after(100, self.read_serial)

    def reset_trial(self):
        """Reset data percobaan"""
        if not self.manual_data and not self.all_trials:
            messagebox.showinfo("Info", "Tidak ada data untuk di-reset")
            return
            
        if messagebox.askyesno("Konfirmasi", "Yakin ingin reset semua data percobaan?"):
            self.manual_data.clear()
            self.all_trials.clear()
            self.setup_plot()
            messagebox.showinfo("Success", "Semua data berhasil di-reset")

    def save_plot(self):
        """Simpan plot sebagai gambar ke folder data/hasil_uji"""
        if not self.manual_data and not self.all_trials:
            messagebox.showwarning("Warning", "Tidak ada data untuk disimpan")
            return
            
        try:
            # Set folder penyimpanan
            save_dir = os.path.join("data", "hasil_uji")
            
            # Buat folder jika belum ada
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # Generate nama file dengan timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(save_dir, f"thrust_plot_{timestamp}.png")
                
            self.fig.savefig(filename, dpi=300, bbox_inches='tight')
            messagebox.showinfo("Success", f"Plot tersimpan di {filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan plot: {str(e)}")

    def save_data(self):
        """Simpan data ke CSV dalam folder data/hasil_uji"""
        if not self.manual_data and not self.all_trials:
            messagebox.showwarning("Warning", "Tidak ada data untuk disimpan")
            return
            
        try:
            # Set folder penyimpanan
            save_dir = os.path.join("data", "hasil_uji")
            
            # Buat folder jika belum ada
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # Generate nama file dengan timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(save_dir, f"thrust_data_{timestamp}.csv")
            
            # Gabungkan semua data dengan label
            all_data = []
            for label, trial_data in self.all_trials.items():
                for data in trial_data:
                    data['label'] = label
                    all_data.append(data)
            
            # Tambahkan data current trial
            for data in self.manual_data:
                data['label'] = self.label_var.get()
                all_data.append(data)
            
            df = pd.DataFrame(all_data)
            df.to_csv(filename, index=False)
            messagebox.showinfo("Success", f"Data tersimpan di {filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan data: {str(e)}")

def run_gui():
    root = tk.Tk()
    root.geometry("900x700")

    app = ThrustTestApp(root)
    root.mainloop()

if __name__ == "__main__":
    run_gui()