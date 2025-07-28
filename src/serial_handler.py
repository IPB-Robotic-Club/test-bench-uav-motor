import serial

def open_serial(port='COM3', baudrate=115200):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Terhubung ke {port} @ {baudrate}bps")
        return ser
    except serial.SerialException as e:
        print(f"Gagal membuka serial: {e}")
        exit(1)