# Test Bench Brushless Motor

# IRC Motor Testing Dashboard

This project is a thrust test bench system for motor and propeller testing. It includes a Python Streamlit dashboard (`app.py`) for serial communication, data logging, and live plotting, along with ESP32/Arduino firmware in `firmware_ver2_ready/firmware_ver2_ready.ino`.

## Repository Structure

- `app.py` - Streamlit dashboard application.
- `firmware_ver2_ready/firmware_ver2_ready.ino` - ESP32 firmware source for motor and load cell control.
- `firmware_ver1/` - older firmware version.
- `load_cell_calib/` - load cell calibration sketch.
- `build/`, `dist/` - build outputs and packaging artifacts.
- `run.py`, `dashboard.py`, `new.py`, `ready.py` - extra scripts in the workspace.

## Overview

The dashboard communicates with the firmware via USB serial at 115200 baud. The firmware controls an ESC-driven motor and reads thrust from an HX711 load cell amplifier. Data is sent back as JSON for live plotting, while status messages are displayed in the serial monitor.

## Requirements

### Python

- Python 3.8+ recommended
- Install dependencies:
  ```bash
  pip install streamlit pyserial pandas
  ```

### Firmware

- ESP32-compatible board
- HX711 load cell amplifier
- ESC / motor
- Load cell mounted to the thrust test rig

## Running the Dashboard

1. Connect the ESP32 board via USB.
2. Install Python dependencies.
3. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```
4. In the app, select the correct COM port.
5. Click `Connect`.

## Dashboard Features

- Connect / Disconnect over serial
- Start / Stop test sequence
- Tare the load cell
- Set manual PWM
- Show live log messages
- Display thrust vs PWM graph
- Auto-refresh every 0.5 seconds

## Firmware Details

The firmware is implemented in `firmware_ver2_ready/firmware_ver2_ready.ino`.

### Pin Configuration

- `MOTOR_PIN` = 25
- `HX711_DT` = 4
- `HX711_SCK` = 5
- `LED_BUILTIN` = 2

### ESC and PWM

- `ESC_MIN_US` = 1000
- `ESC_MAX_US` = 2000
- `PWM_MAX` = 100
- `STEP_SIZE` = 5
- `SAMPLING_MS` = 1000

### Communication Protocol

The firmware listens for newline-terminated serial commands and responds with status or JSON data.

#### Incoming commands

- `START` - begin the test sequence
- `STOP` - stop the test and set motor PWM to 0
- `TARE` - tare the load cell
- `SET_PWM_<value>` - set PWM manually (0-100)
- `SET_CALIB_<factor>` - update the HX711 calibration factor

#### Outgoing messages

- Status lines are prefixed with `STATUS:`
- Data lines are JSON objects:
  ```json
  {"pwm": 25, "gram": 120}
  ```

## How the Firmware Works

- On startup, the firmware initializes the ESC and HX711.
- It performs an initial tare and reports `SYSTEM_READY`.
- When `START` is received, it increments PWM in `STEP_SIZE` steps once per second.
- Each sample sends JSON data for the dashboard plot.
- When PWM exceeds `PWM_MAX`, the test stops and the motor shuts down.

## Notes

- The dashboard stores the last 300 data points and last 100 log lines.
- The serial monitor in `app.py` shows the newest logs first.
- If the firmware is not ready, it reports `HX711_NOT_READY`.

## Next Steps

- Add hardware wiring diagrams.
- Add setup instructions for the ESP32 board and HX711 library.
- Add a calibration guide for the load cell.
