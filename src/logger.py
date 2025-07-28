import pandas as pd
import os
from datetime import datetime


DATA_DIR = 'data/hasil_uji'
FILENAME = f'{DATA_DIR}/thrust_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
buffer = []

def log_to_csv(data):
    buffer.append(data)
    if len(buffer) >= 50:
        df = pd.DataFrame(buffer)
        df.to_csv(FILENAME, mode='a', header=not os.path.exists(FILENAME), index=False)
        buffer.clear()