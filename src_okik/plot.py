import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial
import time
import ast
import tkinter as tk
from tkinter import ttk, filedialog
from serial.tools import list_ports


def get_available_ports():
    return [port.device for port in list_ports.comports()]


class EITApplication:
    def __init__(self, master):
        self.master = master
        master.title("PWM and Gram Plot")
        master.geometry("800x600")

        # --- COM port selection UI ---
        self.com_frame = ttk.Frame(master)
        self.com_frame.pack(pady=10)

        ttk.Label(self.com_frame, text="Select COM Port:").pack(side=tk.LEFT, padx=5)

        self.com_port_var = tk.StringVar()
        self.com_port_combo = ttk.Combobox(self.com_frame, textvariable=self.com_port_var)
        self.com_port_combo['values'] = get_available_ports()
        self.com_port_combo.pack(side=tk.LEFT, padx=5)

        self.start_button = ttk.Button(self.com_frame, text="Start", command=self.start_application)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.save_image_button = ttk.Button(self.com_frame, text="Save Image", command=self.save_image, state='disabled')
        self.save_image_button.pack(side=tk.LEFT, padx=5)

        self.save_data_button = ttk.Button(self.com_frame, text="Save Data", command=self.save_data, state='disabled')
        self.save_data_button.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(master, text="")
        self.status_label.pack()

        # --- Plot setup ---
        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=master)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        self.ser = None
        self.running = False

        self.time_index = []
        self.pwm_values = []
        self.gram_values = []

    def start_application(self):
        selected_port = self.com_port_var.get()
        try:
            self.ser = serial.Serial(selected_port, 115200, timeout=1)
            time.sleep(2)
            self.ser.write(b"START\n")
            self.status_label.config(text="Connected. Receiving data...")
            self.running = True
            self.save_image_button.config(state='normal')
            self.save_data_button.config(state='normal')
            self.master.after(100, self.update_plot)
        except serial.SerialException as e:
            self.status_label.config(text=f"Error: {str(e)}")

    def update_plot(self):
        if not self.running:
            return

        if self.ser and self.ser.in_waiting:
            line = self.ser.readline().decode('utf-8').strip()
            try:
                data = ast.literal_eval(line)
                if 'pwm' in data and 'gram' in data:
                    index = len(self.time_index)
                    self.time_index.append(index)
                    self.pwm_values.append(data['pwm'])
                    self.gram_values.append(data['gram'])

                    self.plot_data()
                    if len(self.time_index) >= 100:
                        self.running = False
                        self.status_label.config(text="Finished collecting 100 data points.")
                        return
                else:
                    print(f"Invalid data: {line}")
            except Exception as e:
                print(f"Error parsing data: {line}, {str(e)}")

        self.master.after(1000, self.update_plot)

    # def plot_data(self):
    #     self.ax.clear()
    #     self.ax.plot(self.time_index, self.pwm_values, label="PWM (%)", color='blue')
    #     self.ax.plot(self.time_index, self.gram_values, label="Weight (gram)", color='green')
    #     self.ax.set_title("PWM and Gram over Time")
    #     self.ax.set_xlabel("Time (s)")
    #     self.ax.set_ylabel("Value")
    #     self.ax.legend()
    #     self.ax.grid(True)
    #     self.canvas.draw()

    def plot_data(self):
        self.ax.clear()
        self.ax.plot(self.pwm_values, self.gram_values, marker='o', linestyle='-', color='purple')
        self.ax.set_title("Correlation: PWM vs Gram")
        self.ax.set_xlabel("PWM (%)")
        self.ax.set_ylabel("Weight (gram)")
        self.ax.grid(True)
        self.canvas.draw()

    def save_image(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG files", "*.png")])
        if file_path:
            self.fig.savefig(file_path)
            self.status_label.config(text=f"Image saved to {file_path}")

    def save_data(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                 filetypes=[("CSV files", "*.csv")])
        if file_path:
            with open(file_path, 'w') as f:
                f.write("Index,PWM,Gram\n")
                for i, (pwm, gram) in enumerate(zip(self.pwm_values, self.gram_values)):
                    f.write(f"{i},{pwm},{gram}\n")
            self.status_label.config(text=f"Data saved to {file_path}")

    def on_closing(self):
        self.running = False
        if self.ser:
            self.ser.close()
        self.master.destroy()


def main():
    root = tk.Tk()
    app = EITApplication(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
