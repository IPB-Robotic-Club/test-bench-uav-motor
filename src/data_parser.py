import ast
import json
import re

def is_boot_log(line):
    boot_keywords = ["boot:", "load:", "rst:", "entry", "SPI_FAST_FLASH_BOOT"]
    return any(key in line for key in boot_keywords)

def is_data_line(line):
    return line.startswith("DATA:") or "pwm" in line and "gram" in line

def parse_data(line):
    line = line.strip()

    if is_boot_log(line):
        return None
    
    if line.startswith("DATA:"):
        line = line[5:].strip()

    # 1. Coba parsing JSON
    try:
        data = json.loads(line)
        if isinstance(data, dict) and "pwm" in data and "gram" in data:
            return {
                "pwm": float(data["pwm"]),
                "gram": float(data["gram"])
            }
    except Exception:
        pass

    # 2. Coba parsing dictionary Python-style
    try:
        data = ast.literal_eval(line)
        if isinstance(data, dict) and "pwm" in data and "gram" in data:
            return {
                "pwm": float(data["pwm"]),
                "gram": float(data["gram"])
            }
    except Exception:
        pass

    # 3. Coba ekstraksi manual pakai regex
    match = re.search(r"pwm\s*[:=]\s*(\d+).*?gram\s*[:=]\s*(\d+)", line)
    if match:
        return {
            "pwm": float(match.group(1)),
            "gram": float(match.group(2))
        }

    # 4. Jika semua gagal
    print(f"⚠️ Format tidak dikenali: {line}")
    return None
