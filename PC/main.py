import math
import numpy as np
import pyaudio
import serial
import serial.tools.list_ports
import time
from threading import Thread

settings = {"mode": 0, "white_multiplier": 3.0, "wobble": 0.5, "smoothing":0.9, "wobble_start":60, "brightness":0.5}

CHUNK = 1024
RATE = 44100
BAUDRATE = 115200

# If this is modified the arduino code needs to be modified as well.
CHANNELS = 2

# If these are modified other parts of this file need to be modified as well
BYTES_PER_SAMPLE = 3
PYAUDIO_FORMAT = pyaudio.paInt24

p = pyaudio.PyAudio()

print('\nAvailable audio devices:\n')
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(f'Device {i + 1}: {info['name']}')

print('\nSelect input device')
input_device = int(input()) - 1
print('Select output device')
output_device = int(input()) - 1

print("\nAvailable ports:\n")

ports = serial.tools.list_ports.comports()
for i, port in enumerate(ports, 1):
    print(f"{i}: {port.device}")

print("\nSelect port")
port = ports[int(input()) - 1]

data = None
new_data = False
running = True

# Pre compute some arrays

frequencies = np.fft.fftfreq(CHUNK, 1 / RATE)[1:CHUNK // 2]
frequencies = frequencies[:frequencies.searchsorted(2000)]

hues = np.arange(0, 6, 6 / len(frequencies))
sectors = hues.astype(np.int32)

r = np.where(sectors == 4, hues % 1, 0)
r = np.where(sectors == 5, 1, r)
r = np.where(sectors == 0, 1, r)
r = np.where(sectors == 1, (-hues) % 1, r)

g = np.where(sectors == 0, hues % 1, 0)
g = np.where(sectors == 1, 1, g)
g = np.where(sectors == 2, 1, g)
g = np.where(sectors == 3, (-hues) % 1, g)

b = np.where(sectors == 2, hues % 1, 0)
b = np.where(sectors == 3, 1, b)
b = np.where(sectors == 4, 1, b)
b = np.where(sectors == 5, (-hues) % 1, b)

color_wheel = np.stack((r, g, b), axis=1).reshape(len(frequencies), 3)
r, g, b = None, None, None

arduino = serial.Serial(port=port.device, baudrate=BAUDRATE, timeout=1)

def relay():
    global new_data#, history

    while not new_data:
        time.sleep(0)

    rgb_last = np.zeros((CHANNELS, 3,))
    wobble_last = np.zeros((CHANNELS,), dtype=np.bool)
    maxes = [1] * int(60 * RATE / CHUNK)

    while running:
        new_data = False

        d = np.frombuffer(data, dtype=np.uint8).reshape(CHUNK, CHANNELS, BYTES_PER_SAMPLE)
        d2 = d.astype(np.uint32)
        values = d2[:, :, 0] | (d2[:, :, 1] << 8) | (d2[:, :, 2] << 16)

        # Extend sign
        sign_mask = d[:, :, 2] & 0x80
        values = np.where(sign_mask, values | 0xFF000000, values).astype(np.int32)

        frequency_values = np.absolute(np.fft.fft(values, axis=0)[1:len(frequencies)+1])
        frequency_values = frequency_values.reshape(len(frequencies), CHANNELS, 1) # Make broadcastable to color_wheel

        # Compute colors

        wobble = np.zeros((CHANNELS,), dtype=np.bool)

        if settings["mode"] == 0:
            indexes = frequency_values.argmax(axis=0)[:, 0]
            peak_frequency_values = frequency_values[indexes, np.arange(CHANNELS), :]

            rgb = color_wheel[indexes] * peak_frequency_values
            white_factor = frequency_values.mean(axis=0) / peak_frequency_values * settings["white_multiplier"]
            rgb += (peak_frequency_values - rgb) * white_factor

            wobble = frequencies[indexes] < settings["wobble_start"]

        assert rgb.shape == (CHANNELS, 3)

        # Post processing

        rgb_last *= settings["smoothing"]

        wobble = np.where(rgb[:, 0] < rgb_last[:, 0], wobble_last, wobble)
        assert wobble.shape == (CHANNELS,)

        rgb = np.where(rgb > rgb_last, rgb, rgb_last)
        rgb_last = rgb.copy()
        wobble_last = wobble

        cmax = rgb.max(axis=0).max(axis=0)
        if cmax > 0:
            maxes = maxes[1:] + [cmax]
        # Format to send

        rgb *= 255 / max(maxes) * settings["brightness"]
        rgb = rgb.astype(np.int32)

        if new_data:
            print("Output is too slow.")

        # Broadcast

        while not new_data:
            m = settings["wobble"] * 0.5
            wobble_mult = np.where(wobble, math.sin(time.monotonic() * 2 * math.pi * 16) * m + 1 - m, 1).reshape(CHANNELS, 1)

            arduino.write(bytes([42]))
            arduino.write(bytes((rgb * wobble_mult).reshape(CHANNELS * 3).astype(np.int32).tolist()))

            if arduino.read() != bytes([42]):
                print("Invalid confirmation from arduino")

            time.sleep(0)

arduino_thread = Thread(target=relay)
arduino_thread.start()

def callback(in_data, frame_count, time_info, status_flags):
    global data, new_data, last
    data = in_data
    new_data = True

    return in_data, pyaudio.paContinue

stream = p.open(format=p.get_format_from_width(BYTES_PER_SAMPLE),
                channels=CHANNELS,
                rate=RATE,
                input=True,
                output=True,
                frames_per_buffer=CHUNK,
                input_device_index=input_device,
                output_device_index=output_device,
                stream_callback=callback)

print('Relaying. Press enter to stop. Type SETTING=value to change settings')

while running:
    a = input()
    if not "=" in a:
        running = False
    else:
        a = a.split("=")
        if a[0] in settings:
            if type(settings[a[0]]) == int:
                settings[a[0]] = int(a[1])
            elif type(settings[a[0]]) == float:
                settings[a[0]] = float(a[1])
            print(f"Setting { a[0] } set to { settings[a[0]] }")

print('Stopping')

running = False

stream.close()
p.terminate()
arduino_thread.join()
arduino.write(bytes([42, 0, 0, 0]))
arduino.close()