import tkinter as tk
import pandas as pd
from tkinter import filedialog, messagebox
from src.serial_utils import get_available_ports
from src.serial_handler import open_serial
from src.data_parser import parse_data
from src.logger import log_to_csv
from src.plotter import setup_embedded_plot, update_embedded_plot, trial_buffers, fig, ax

class ThrustTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Thrust vs PWM Monitor - Multi Percobaan")
        self.manual_data = []

        # Frame Port
        self.port_frame = tk.Frame(root)
        self.port_frame.pack(pady=10)
        tk.Label(self.port_frame, text="Pilih COM Port:").pack(side=tk.LEFT)
        self.com_port_var = tk.StringVar() #memilih port serial 
        ports = get_available_ports() #cek port serial yang tersedia
        self.com_dropdown = tk.OptionMenu(self.port_frame, self.com_port_var, *ports)
        self.com_dropdown.pack(side=tk.LEFT)
        if ports:
            self.com_port_var.set(ports[0])

        # Frame Label Percobaan
        self.label_frame = tk.Frame(root)
        self.label_frame.pack(pady=5)
        tk.Label(self.label_frame, text="Label Percobaan:").pack(side=tk.LEFT)
        self.trial_label_var = tk.StringVar(value="Percobaan 1") #label unik
        self.trial_entry = tk.Entry(self.label_frame, textvariable=self.trial_label_var, width=20)
        self.trial_entry.pack(side=tk.LEFT)

        # Checkbox Gunakan Dummy
        self.use_dummy_var = tk.BooleanVar() 
        self.dummy_checkbox = tk.Checkbutton(root, text="Gunakan Dummy Data", variable=self.use_dummy_var)
        self.dummy_checkbox.pack(pady=5)

        # Frame Kontrol
        self.control_frame = tk.Frame(root)
        self.control_frame.pack(pady=5)
        self.start_btn = tk.Button(self.control_frame, text="Mulai", command=self.start_test, bg='green', fg='white')
        self.stop_btn = tk.Button(self.control_frame, text="Stop", command=self.stop_test, bg='red', fg='white')
        self.real_btn = tk.Button(self.control_frame, text="Mode REAL (Sensor)", command=self.send_real_mode)
        self.dummy_mode_btn = tk.Button(self.control_frame, text="Mode DUMMY (ESP)", command=self.send_dummy_mode)
        self.reset_trial_btn = tk.Button(self.control_frame, text="Reset Percobaan", command=self.reset_current_trial, bg='orange')
        self.save_img_btn = tk.Button(self.control_frame, text="Simpan Gambar", command=self.save_plot_as_image)
        self.save_data_btn = tk.Button(self.control_frame, text="Simpan Data CSV", command=self.save_data_to_csv)
        for btn in [self.start_btn, self.stop_btn, self.real_btn, self.dummy_mode_btn, self.reset_trial_btn, self.save_img_btn, self.save_data_btn]:
            btn.pack(side=tk.LEFT, padx=5)

        self.canvas = setup_embedded_plot(root)

        self.use_dummy_var.trace_add("write", lambda *_: self.update_mode_buttons())
        self.update_mode_buttons()

        self.running = False
        self.ser = None

    def update_mode_buttons(self):
        if self.use_dummy_var.get():
            self.real_btn.config(state=tk.DISABLED)
            self.dummy_mode_btn.config(state=tk.DISABLED)
        else:
            self.real_btn.config(state=tk.NORMAL)
            self.dummy_mode_btn.config(state=tk.NORMAL)

    def start_test(self):
        self.running = True
        try:
            if self.use_dummy_var.get():
                from src.dummy_serial import DummySerial
                label = self.trial_label_var.get().strip()
                self.ser = DummySerial(label=label)  # default mode 'linear'
                print(f"Dummy '{label}' Aktif 🚨")
            else:
                port = self.com_port_var.get()
                if not port:
                    messagebox.showwarning("Port Tidak Dipilih", "Silakan pilih COM port terlebih dahulu.")
                    return
                self.ser = open_serial(port)
                self.ser.write(b"START\n")
            self.read_serial()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def stop_test(self):
        self.running = False
        try:
            if self.ser:
                self.ser.close()
                print("Serial ditutup.")
        except Exception as e:
            print(f"⚠️ Gagal tutup serial: {e}")
        messagebox.showinfo("Stop", "Pengujian dihentikan.")

    def send_real_mode(self):
        if self.ser:
            try:
                self.ser.write(b"REAL\n")
                print("Mode REAL dikirim")
            except Exception as e:
                print(f"⚠️ Gagal kirim perintah REAL: {e}")

    def send_dummy_mode(self):
        if self.ser:
            try:
                self.ser.write(b"DUMMY\n")
                print("Mode DUMMY dikirim")
            except Exception as e:
                print(f"⚠️ Gagal kirim perintah DUMMY: {e}")

    def read_serial(self):
        if self.running and getattr(self.ser, "in_waiting", True):
            try:
                raw = self.ser.readline()
                if not raw:
                    if hasattr(self.ser, "is_finished") and self.ser.is_finished():
                        print(f"✅ Dummy '{self.ser.label}' telah selesai.")
                        self.stop_test()
                        return
                    return

                decoded = raw.decode().strip()
                if not decoded:
                    return

                data = parse_data(decoded)
                label = self.ser.label if self.use_dummy_var.get() else self.trial_label_var.get().strip()
                if data and isinstance(data, dict):
                    log_to_csv(data)
                    self.manual_data.append(data)
                    update_embedded_plot(data, label)
            except Exception as e:
                print(f"⚠️ Gagal baca atau parse data serial: {e}")

        if self.running:
            self.root.after(100, self.read_serial) #loop baca setiap 100 ms

    def reset_current_trial(self):
        label = self.trial_label_var.get().strip()
        if not label:
            messagebox.showwarning("Label Kosong", "Silakan isi label percobaan.")
            return

        buffer = trial_buffers.get(label)
        if not buffer or not buffer.get("pwm"):
            messagebox.showwarning("Data Tidak Ditemukan", f"Tidak ada data untuk '{label}'.")
            return

        buffer["pwm"].clear()
        buffer["gram"].clear()

        ax.clear()
        for name, buffer in trial_buffers.items():
            if buffer["pwm"]:
                ax.plot(buffer["pwm"], buffer["gram"], label=name)

        ax.set_xlabel("PWM (%)")
        ax.set_ylabel("Thrust (gram)")
        ax.set_title(f"Percobaan '{label}' di-reset")
        ax.grid(True)
        ax.legend()
        fig.canvas.draw()

        messagebox.showinfo("Reset Berhasil", f"Grafik untuk percobaan '{label}' telah dihapus dan siap diulang.")

    def save_plot_as_image(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if file_path:
            fig.savefig(file_path)
            messagebox.showinfo("Berhasil", f"Gambar disimpan di {file_path}")

    def save_data_to_csv(self):
        if not self.manual_data:
            messagebox.showwarning("Tidak Ada Data", "Belum ada data untuk disimpan.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            df = pd.DataFrame(self.manual_data)
            df.to_csv(file_path, index=False)
            messagebox.showinfo("Berhasil", f"Data disimpan ke {file_path}")

def run_gui():
    root = tk.Tk()
    app = ThrustTestApp(root)
    root.mainloop()