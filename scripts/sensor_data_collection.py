import asyncio
import collections
import queue
import threading
import os
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from bleak import BleakScanner, BleakClient

import sqlite3
import numpy as np
import time
import os

# Locate master_datasets/fall_data.db from the scripts/ directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Navigate up one level from 'scripts' to root, then into 'master_datasets'
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "master_datasets", "fall_data.db"))

# Connect to SQLite
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Initialize Table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS fall_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        worker_id TEXT,
        acc_magnitude REAL,
        gyro_magnitude REAL,
        fall_detected INTEGER
    )
''')
conn.commit()

def log_reading(worker_id, acc, gyro, acc_thresh=3.0, gyro_thresh=400.0):
    is_fall = 1 if (acc >= acc_thresh and gyro >= gyro_thresh) else 0
    cursor.execute(
        "INSERT INTO fall_events (worker_id, acc_magnitude, gyro_magnitude, fall_detected) VALUES (?, ?, ?, ?)",
        (worker_id, float(acc), float(gyro), is_fall)
    )
    conn.commit()

print(f"🚀 Starting telemetry generator. Logging to SQLite database at:\n   {DB_PATH}\n")

workers = ["eishmeet", "kyle", "jerry", "kevin"]

try:
    while True:
        for worker in workers:
            if np.random.rand() > 0.95:
                acc = np.random.uniform(3.0, 6.0)
                gyro = np.random.uniform(400.0, 900.0)
            else:
                acc = np.random.uniform(0.8, 2.2)
                gyro = np.random.uniform(20.0, 250.0)
            
            log_reading(worker, acc, gyro)
        
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped simulation.")
    conn.close()

import sqlite3
import os
import time
import serial
import serial.tools.list_ports

# ---------------------------------------------------------
# 1. Locate SQLite DB (master_datasets/fall_data.db)
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "master_datasets", "fall_data.db"))

# Connect to SQLite
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Initialize Table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS fall_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        worker_id TEXT,
        acc_magnitude REAL,
        gyro_magnitude REAL,
        fall_detected INTEGER
    )
''')
conn.commit()

def log_reading(worker_id, acc, gyro, acc_thresh=3.0, gyro_thresh=400.0):
    is_fall = 1 if (acc >= acc_thresh and gyro >= gyro_thresh) else 0
    cursor.execute(
        "INSERT INTO fall_events (worker_id, acc_magnitude, gyro_magnitude, fall_detected) VALUES (?, ?, ?, ?)",
        (worker_id, float(acc), float(gyro), is_fall)
    )
    conn.commit()

# ---------------------------------------------------------
# 2. Configure Serial Port
# ---------------------------------------------------------
# Set your Arduino COM port (e.g., 'COM3', 'COM4' on Windows or '/dev/ttyUSB0' on Linux)
COM_PORT = "COM3"  
BAUD_RATE = 115200

# Helper to automatically detect available COM ports if needed
ports = [port.device for port in serial.tools.list_ports.comports()]
print(f"Available serial ports: {ports}")

try:
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    print(f"✅ Connected to Arduino Nesso on {COM_PORT} at {BAUD_RATE} baud.")
except Exception as e:
    print(f"❌ Failed to connect to {COM_PORT}: {e}")
    print("Please check your COM port in Arduino IDE and update COM_PORT in this script.")
    exit(1)

# ---------------------------------------------------------
# 3. Live Serial Reading Loop
# ---------------------------------------------------------
WORKER_ID = "eishmeet"

print(f"🚀 Streaming LIVE telemetry from Arduino to {DB_PATH}...\n")

try:
    while True:
        if ser.in_waiting > 0:
            # Read a line from Serial (expected format: "acc_val,gyro_val")
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            
            if line:
                try:
                    # Split incoming CSV format: e.g. "1.25,45.0"
                    parts = line.split(',')
                    if len(parts) == 2:
                        acc = float(parts[0])
                        gyro = float(parts[1])
                        
                        # Log real physical sensor readings into SQLite
                        log_reading(WORKER_ID, acc, gyro)
                        print(f"Logged -> Worker: {WORKER_ID} | Acc: {acc:.2f}g | Gyro: {gyro:.2f}°/s")
                except ValueError:
                    # Ignore headers or malformed debug strings from Arduino
                    pass

        time.sleep(0.05)  # Fast polling interval

except KeyboardInterrupt:
    print("\nStopping Arduino listener.")
    ser.close()
    conn.close()