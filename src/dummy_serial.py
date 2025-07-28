import json
import random
import time

class DummySerial:
    def __init__(self, label="Motor A", motor_type="default", max_pwm=100, loop=False, use_noise=True, delay=0.1):
        self.label = label
        self.motor_type = motor_type  # e.g. 'plastic_1045', 'plastic_1245', 'carbon_1245'
        self.max_pwm = max_pwm
        self.loop = loop
        self.use_noise = use_noise
        self.delay = delay

        self.pwm = 0
        self.stopped = False

    def readline(self):
        if self.stopped:
            if self.loop:
                self.reset()
            else:
                return b''

        pwm = self._generate_pwm()
        rpm = pwm * 54  # Simulasi RPM berdasarkan PWM
        gram = self._simulate_thrust(rpm)

        time.sleep(self.delay)
        payload = {
            'motor': self.label,
            'pwm': pwm,
            'rpm': round(rpm, 2),
            'gram': round(gram, 2)
        }
        return json.dumps(payload).encode()

    def _generate_pwm(self):
        pwm = self.pwm + random.randint(2, 5)
        pwm = min(pwm, self.max_pwm)
        if pwm >= self.max_pwm:
            self.stopped = True
        self.pwm = pwm
        return pwm

    def _simulate_thrust(self, rpm):
        # Thrust curve berdasarkan tipe motor
        if self.motor_type == "plastic_1045":
            gram = 0.00004 * rpm**2 + 10
        elif self.motor_type == "plastic_1245":
            gram = 0.00005 * rpm**2 + 20
        elif self.motor_type == "carbon_1245":
            gram = 0.01000 * rpm**2 + 50
        else:
            gram = 0.000043 * rpm**2 + 12

        if self.use_noise and not self.stopped:
            gram += random.uniform(-8, 8)
        return max(gram, 0)

    def reset(self):
        self.pwm = 0
        self.stopped = False

    def is_finished(self):
        return self.stopped

    def close(self):
        pass

# 👇 Auto-run untuk 3 dummy sekaligus
if __name__ == "__main__":
    motors = [
        DummySerial(label="1045 ABS Plastik", motor_type="plastic_1045"),
        DummySerial(label="1245 ABS Plastik", motor_type="plastic_1245"),
        DummySerial(label="1245 Carbon Fiber", motor_type="carbon_1245")
    ]

    while not all(motor.is_finished() for motor in motors):
        for motor in motors:
            if not motor.is_finished():
                line = motor.readline()
                print(line.decode())