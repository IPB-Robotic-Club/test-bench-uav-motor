import ast
import json
import re

def parse_data(line):
    line = line.strip()

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
