import asyncio
import collections
import queue
import threading
import os
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from bleak import BleakScanner, BleakClient

# ==============================================================================
# ===== HARDCODED CONFIGURATION (NO MORE PROMPTS) ==============================
# ==============================================================================

# 1. REPLACE THIS with your exact Arduino Bluetooth name
DEVICE_NAME = "241504D"

# 2. Automatically create a unique, permanent file name using the timestamp
timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE_NAME = f"imu_log_{timestamp_str}.csv"
FOLDER_PATH = "C:\\temp"
FILE_PATH = os.path.join(FOLDER_PATH, LOG_FILE_NAME)

# Ensure the C:\temp directory exists so Python doesn't crash
os.makedirs(FOLDER_PATH, exist_ok=True)

# Open the text file for permanent recording
try:
    file = open(FILE_PATH, "w")
    file.write("Timestamp,AccX,AccY,AccZ,GyroX,GyroY,GyroZ\n")  # CSV Header
    print(f"🚀 Success! Permanent logfile created at: {FILE_PATH}")
except Exception as e:
    print(f"❌ Could not open file at {FILE_PATH}: {e}")
    exit(1)

# BLE UUIDs
SERIVCE_UUID = "b3834f93-a249-44fa-b8bd-24eeeea66ef1"
ACCELNGYRO_UUID = "f509416c-3c4b-401e-a768-b25a9e621a91"

# ==============================================================================
# ==============================================================================

# Thread-safe queue to pass data from BLE thread to Plot thread
data_queue = queue.Queue()

# Deques to store the last N data points for the moving window graph
MAX_POINTS = 200
time_data = collections.deque(maxlen=MAX_POINTS)
acc_x, acc_y, acc_z = [collections.deque(maxlen=MAX_POINTS) for _ in range(3)]
gyro_x, gyro_y, gyro_z = [collections.deque(maxlen=MAX_POINTS) for _ in range(3)]


def notification_handler(characteristic, data):
    """Callback triggered whenever BLE data arrives."""
    try:
        # Decode the raw bytes directly to a string
        raw_string = data.decode('utf-8').strip()

        # DIAGNOSTIC PRINT: See exactly what the Arduino is broadcasting
        print(f"📡 RAW DATA FROM ARDUINO: '{raw_string}'")

        # Try to parse it
        floats = [float(i) for i in raw_string.split(',')]

        if len(floats) == 6:
            data_queue.put(floats)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            file.write(f"{timestamp},{','.join(map(str, floats))}\n")
            file.flush()
        else:
            print(f"⚠️ Warning: Expected 6 numbers, but got {len(floats)} columns instead.")

    except Exception as e:
        print(f"❌ Parsing Error: Could not convert data to numbers. Details: {e}")


async def run_ble():
    """Scans and connects to the BLE device."""
    print(f"Scanning for '{DEVICE_NAME}'...")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if not device:
        print(f"Device '{DEVICE_NAME}' not found. Make sure it is powered on.")
        return

    print(f"Connected to {device.name} [{device.address}]")
    async with BleakClient(device) as client:
        await client.start_notify(ACCELNGYRO_UUID, notification_handler)
        print("Data streaming live... (Close the graph window to stop and save)")

        while True:
            await asyncio.sleep(1)


def start_ble_loop():
    """Target function for the background thread."""
    asyncio.run(run_ble())


# Set up the Matplotlib figure with 2 subplots (Accel & Gyro)
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))
fig.suptitle(f"Real-time IMU Data ({DEVICE_NAME})", fontsize=14)

# Setup empty line plots
line_ax, = ax1.plot([], [], label='Acc X', color='r')
line_ay, = ax1.plot([], [], label='Acc Y', color='g')
line_az, = ax1.plot([], [], label='Acc Z', color='b')

line_gx, = ax2.plot([], [], label='Gyro X', color='c')
line_gy, = ax2.plot([], [], label='Gyro Y', color='m')
line_gz, = ax2.plot([], [], label='Gyro Z', color='y')


def init_plot():
    """Initialize plot styling."""
    ax1.set_ylabel("Acceleration (g)")
    ax1.legend(loc="upper left")
    ax1.grid(True)

    ax2.set_ylabel("Rotation (deg/s)")
    ax2.set_xlabel("Data Samples")
    ax2.legend(loc="upper left")
    ax2.grid(True)

    return line_ax, line_ay, line_az, line_gx, line_gy, line_gz


def update_plot(frame):
    """Called periodically by FuncAnimation to refresh the frame."""
    while not data_queue.empty():
        try:
            f1, f2, f3, f4, f5, f6 = data_queue.get_nowait()
            next_x = time_data[-1] + 1 if time_data else 0
            time_data.append(next_x)

            acc_x.append(f1)
            acc_y.append(f2)
            acc_z.append(f3)
            gyro_x.append(f4)
            gyro_y.append(f5)
            gyro_z.append(f6)
        except queue.Empty:
            break

    if time_data:
        line_ax.set_data(time_data, acc_x)
        line_ay.set_data(time_data, acc_y)
        line_az.set_data(time_data, acc_z)

        line_gx.set_data(time_data, gyro_x)
        line_gy.set_data(time_data, gyro_y)
        line_gz.set_data(time_data, gyro_z)

        for ax in (ax1, ax2):
            ax.set_xlim(time_data[0], time_data[-1])
            ax.relim()
            ax.autoscale_view(scalex=False, scaley=True)

    return line_ax, line_ay, line_az, line_gx, line_gy, line_gz


if __name__ == "__main__":
    # 1. Spin up the Bluetooth operations in the background
    ble_thread = threading.Thread(target=start_ble_loop, daemon=True)
    ble_thread.start()

    # 2. Run the live animation on the Main Thread
    ani = FuncAnimation(fig, update_plot, init_func=init_plot, blit=False, interval=20, cache_frame_data=False)

    try:
        plt.show()
    finally:
        print(f"Closing file. Data safely stored permanently at: {FILE_PATH}")
        file.close()