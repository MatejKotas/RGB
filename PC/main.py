import math
import numpy as np
import pyaudio
import serial
import serial.tools.list_ports
import time
from threading import Thread

settings = {"mode": 0, "white_multiplier": 1.0, "wobble": 0.25, "smoothing":0.5, "wobble_start":60, "brightness":0.5, "bass_start":250, "bass_multiplier":1.0}

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

def input_number(type, lower, upper):
    while True:
        a = input()
        try:
            b = type(a)

            if lower <= b <= upper:
                return b
            else:
                print("Number out of range.")

        except ValueError:
            print("Number could not be parsed.")

print('\nSelect input device')
input_device = input_number(int, 1, p.get_device_count()) - 1
print('Select output device')
output_device = input_number(int, 1, p.get_device_count()) - 1

print("\nAvailable ports:\n")

ports = serial.tools.list_ports.comports()
for i, port in enumerate(ports, 1):
    print(f"{i}: {port.device}")

print("\nSelect port")
port_index = input_number(int, 1, len(ports)) - 1
port = ports[port_index]

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

def connect_to_arduino():
    fail = False
    while True:
        try:
            arduino = serial.Serial(port=port.device, baudrate=BAUDRATE, timeout=1)
            if fail:
                print("Connected.")
            return arduino
        except:
            if not running:
                return None
            print("Could not connect to microcontroller. Retrying in 5 seconds.")
            fail = True
            for _ in range(50):
                time.sleep(0.1)
                if not running:
                    return None

arduino = None

def relay():
    global new_data, arduino

    arduino = connect_to_arduino()

    while running and not new_data:
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
            frequency_values[frequencies < settings["bass_start"], :, :] *= settings["bass_multiplier"]
            peak_frequency_values = frequency_values[indexes, np.arange(CHANNELS), :]

            rgb = color_wheel[indexes] * peak_frequency_values

            peak_frequency_values = np.where(peak_frequency_values == 0, 1, peak_frequency_values) # Avoid divide by 0
            white_factor = frequency_values.mean(axis=0) / peak_frequency_values * settings["white_multiplier"]
            rgb += (peak_frequency_values - rgb) * white_factor

            wobble = frequencies[indexes] < settings["wobble_start"]

        assert rgb.shape == (CHANNELS, 3)

        # Post processing

        cmax = rgb.max(axis=0).max(axis=0)
        if cmax > 1: # Avoid divide by 0
            maxes = maxes[1:] + [cmax]
        cmax = max(maxes)

        rgb_last -= cmax * CHUNK / RATE / settings["smoothing"]
        rgb_last = np.where(rgb_last < 0, 0, rgb_last)

        rgb = np.where(rgb > rgb_last, rgb, rgb_last)
        rgb_last = rgb.copy()

        wobble = np.where(rgb[:, 0] < rgb_last[:, 0], wobble_last, wobble)
        assert wobble.shape == (CHANNELS,)
        wobble_last = wobble

        # Format to send

        rgb *= 255 / cmax * settings["brightness"]
        rgb = rgb.astype(np.int32)

        # Broadcast

        while not new_data:
            m = settings["wobble"] * 0.5
            wobble_mult = np.where(wobble, math.sin(time.monotonic() * 2 * math.pi * 16) * m + 1 - m, 1).reshape(CHANNELS, 1)

            try:
                arduino.write(bytes([42]))
                arduino.write(bytes((rgb * wobble_mult).reshape(CHANNELS * 3).astype(np.int32).tolist()))

                if arduino.read() != bytes([42]):
                    print("Invalid confirmation from arduino.")
            except:
                print("Microcontroller disconnected.")
                arduino = None
                arduino = connect_to_arduino()

            time.sleep(0)

arduino_thread = Thread(target=relay)
arduino_thread.start()

def callback(in_data, frame_count, time_info, status_flags):
    global data, new_data, last
    data = in_data
    new_data = True

    return in_data, pyaudio.paContinue

stream = None

try:
    stream = p.open(format=p.get_format_from_width(BYTES_PER_SAMPLE),
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    output=True,
                    frames_per_buffer=CHUNK,
                    input_device_index=input_device,
                    output_device_index=output_device,
                    stream_callback=callback)
except:
    print("Could not open stream.")
    running = False

else:
    print('Relaying. Input setting=value to change settings. Input "exit" to exit')

while running:
    a = input()
    if a == "exit":
        running = False
    else:
        a = a.split("=")
        if len(a) == 2 and a[0] in settings:
            try:
                if type(settings[a[0]]) == int:
                    settings[a[0]] = int(a[1])
                elif type(settings[a[0]]) == float:
                    settings[a[0]] = float(a[1])
                print(f"Setting { a[0] } set to { settings[a[0]] }")

            except ValueError:
                print("Input not recognized.")
        else:
            print("Input not recognized.")

print('Stopping.')

running = False

if stream:
    stream.close()
p.terminate()
arduino_thread.join()

if arduino != None:
    arduino.write(bytes([42]))
    arduino.write(bytes([0] * (CHANNELS * 3)))
    arduino.read()
    arduino.close()