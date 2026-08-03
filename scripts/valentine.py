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
# ===== WORKSPACE CONFIGURATION ================================================
# ==============================================================================

DEVICE_NAME = "Kevin's Nesso"  # Matches your Arduino BLE local name

# Dynamically save files relative to where this project folder lives
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDER_PATH = os.path.join(BASE_DIR, "data_logs")
os.makedirs(FOLDER_PATH, exist_ok=True)

timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
FILE_PATH = os.path.join(FOLDER_PATH, f"imu_log_{timestamp_str}.csv")
IMAGE_PATH = os.path.join(FOLDER_PATH, f"imu_graph_{timestamp_str}.png")

try:
    file = open(FILE_PATH, "w")
    file.write("Timestamp,AccX,AccY,AccZ,GyroX,GyroY,GyroZ\n")
    print(f"🚀 CSV Logfile initiated inside workspace: {FILE_PATH}")
except Exception as e:
    print(f"❌ Could not create logfile: {e}")
    exit(1)

ACCELNGYRO_UUID = "f509416c-3c4b-401e-a768-b25a9e621a91"

# ==============================================================================

data_queue = queue.Queue()
MAX_POINTS = 500
time_data = collections.deque(maxlen=MAX_POINTS)
acc_x, acc_y, acc_z = [collections.deque(maxlen=MAX_POINTS) for _ in range(3)]
gyro_x, gyro_y, gyro_z = [collections.deque(maxlen=MAX_POINTS) for _ in range(3)]

def notification_handler(characteristic, data):
    try:
        raw_string = data.decode('utf-8').strip()
        floats = [float(i) for i in raw_string.split(',')]
        if len(floats) == 6:
            data_queue.put(floats)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            file.write(f"{timestamp},{','.join(map(str, floats))}\n")
            file.flush() 
    except Exception as e:
        pass  # Silently handle transient packet drops

async def run_ble():
    print(f"🔍 [VS Code BLE Engine] Scanning for '{DEVICE_NAME}'...")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    
    if not device:
        print(f"❌ Device '{DEVICE_NAME}' not found. Verify it isn't paired to Windows.")
        return

    print(f"✅ Connected to {device.name} [{device.address}]")
    async with BleakClient(device) as client:
        await client.start_notify(ACCELNGYRO_UUID, notification_handler)
        print("📊 Data streaming live. Close the pop-up graph window to terminate and save.")
        while True:
            await asyncio.sleep(1)

# Set up Matplotlib figure engine 
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(11, 7))
fig.suptitle(f"Real-time IMU Data Analysis ({DEVICE_NAME})", fontsize=14, fontweight='bold')

line_ax, = ax1.plot([], [], label='Acc X', color='#d62728', linewidth=1.5)
line_ay, = ax1.plot([], [], label='Acc Y', color='#2ca02c', linewidth=1.5)
line_az, = ax1.plot([], [], label='Acc Z', color='#1f77b4', linewidth=1.5)

line_gx, = ax2.plot([], [], label='Gyro X', color='#17becf', linewidth=1.5)
line_gy, = ax2.plot([], [], label='Gyro Y', color='#e377c2', linewidth=1.5)
line_gz, = ax2.plot([], [], label='Gyro Z', color='#bcbd22', linewidth=1.5)

def init_plot():
    ax1.set_ylabel("Acceleration (g)", fontsize=11)
    ax1.legend(loc="upper left")
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax2.set_ylabel("Rotation (deg/s)", fontsize=11)
    ax2.set_xlabel("Data Samples", fontsize=11)
    ax2.legend(loc="upper left")
    ax2.grid(True, linestyle='--', alpha=0.6)
    return line_ax, line_ay, line_az, line_gx, line_gy, line_gz

def update_plot(frame):
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

def on_close(event):
    print("\n💾 Finalizing data storage loops...")
    try:
        fig.tight_layout(rect=[0, 0.03, 1, 0.95])
        fig.savefig(IMAGE_PATH, dpi=300)
        print(f"📊 Live graph snapshot saved successfully to:\n   -> {IMAGE_PATH}")
    except Exception as e:
        print(f"⚠️ Failed to export graph snapshot: {e}")

fig.canvas.mpl_connect('close_event', on_close)

if __name__ == "__main__":
    ble_thread = threading.Thread(target=lambda: asyncio.run(run_ble()), daemon=True)
    ble_thread.start()

    ani = FuncAnimation(fig, update_plot, init_func=init_plot, blit=False, interval=20, cache_frame_data=False)
    
    try:
        plt.show()
    finally:
        file.close()
        print(f"🔒 Data streams safely closed. Logfile preserved at:\n   -> {FILE_PATH}")