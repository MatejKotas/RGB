import asyncio
import math
import numpy as np
import pyaudio
import serial
import serial.tools.list_ports
import time

# CHUNK = 1024
# RATE = 44100
# BAUDRATE = 115200

# If this is modified the arduino code needs to be modified as well.
CHANNELS = 2

# If these are modified other parts of this file need to be modified as well
BYTES_PER_SAMPLE = 3
PYAUDIO_FORMAT = pyaudio.paInt24

class RGB:
    def __init__(self, CHUNK=1024, RATE=44100, BAUDRATE=115200, settings=None, exit_callback=None, sound_start_callback=None, setting_changed_callback=None, commands={}):
        if settings == None:
            settings = {"mode": 0, "white_multiplier": 1.0, "wobble": 0.5, "smoothing":1.0, "wobble_start":60, "brightness":0.5, "bass_start":250, "bass_multiplier":1.0, "minimum":"#000000", "white":"#FFE650"}

        self.CHUNK = CHUNK
        self.RATE = RATE
        self.BAUDRATE = BAUDRATE
        self.settings = settings

        self.exit_callback = exit_callback
        self.sound_start_callback = sound_start_callback
        self.commands = commands
        self.setting_changed_callback = setting_changed_callback

        self.new_data = False
        self.running = True
        self.arduino = None

        self.p = pyaudio.PyAudio()

        # Pre compute some arrays

        self.frequencies = np.fft.fftfreq(CHUNK, 1 / RATE)[1:CHUNK // 2]
        self.frequencies = self.frequencies[:self.frequencies.searchsorted(2000)]

        hues = np.arange(0, 6, 6 / len(self.frequencies))
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

        self.color_wheel = np.stack((r, g, b), axis=1).reshape(len(self.frequencies), 3)

    async def input(self):
        return await self.loop.run_in_executor(None, input)

    async def input_number(self, type, lower, upper):
        while True:
            a = await self.input()
            try:
                b = type(a)

                if lower <= b <= upper:
                    return b
                else:
                    print("Number out of range.")

            except ValueError:
                print("Number could not be parsed.")

    async def connect_to_arduino(self, print_message=False):
        fail = False
        while True:
            try:
                self.arduino = await self.loop.run_in_executor(None, lambda: serial.Serial(port=self.port.device, baudrate=self.BAUDRATE, timeout=1))
                if print_message or fail:
                    print("Connected.")
                return

            except:
                print("Could not connect to microcontroller. Retrying in 5 seconds.")
                fail = True
                for _ in range(50):
                    await asyncio.sleep(0.1)
                    if not self.running:
                        return

    async def relay(self):
        await self.connect_to_arduino()

        while not self.new_data:
            await asyncio.sleep(0)

        rgb_last = np.zeros((CHANNELS, 3,))
        wobble_last = np.zeros((CHANNELS,), dtype=np.bool)
        maxes = [1] * int(60 * self.RATE / self.CHUNK)
        silent = False

        while self.running:
            self.new_data = False

            d = np.frombuffer(self.data, dtype=np.uint8).reshape(self.CHUNK, CHANNELS, BYTES_PER_SAMPLE)
            d2 = d.astype(np.uint32)
            values = d2[:, :, 0] | (d2[:, :, 1] << 8) | (d2[:, :, 2] << 16)

            # Extend sign
            sign_mask = d[:, :, 2] & 0x80
            values = np.where(sign_mask, values | 0xFF000000, values).astype(np.int32)

            frequency_values = np.absolute(np.fft.fft(values, axis=0)[1:len(self.frequencies)+1])
            frequency_values = frequency_values.reshape(len(self.frequencies), CHANNELS, 1) # Make broadcastable to color_wheel

            # Compute colors

            wobble = np.zeros((CHANNELS,), dtype=np.bool)

            if self.settings["mode"] == 0:
                indexes = frequency_values.argmax(axis=0)[:, 0]
                frequency_values[self.frequencies < self.settings["bass_start"], :, :] *= self.settings["bass_multiplier"]
                peak_frequency_values = frequency_values[indexes, np.arange(CHANNELS), :]

                rgb = self.color_wheel[indexes] * peak_frequency_values

                peak_frequency_values = np.where(peak_frequency_values == 0, 1, peak_frequency_values) # Avoid divide by 0
                white_factor = frequency_values.mean(axis=0) / peak_frequency_values * self.settings["white_multiplier"]
                rgb += (peak_frequency_values - rgb) * white_factor

                wobble = self.frequencies[indexes] < self.settings["wobble_start"]

            assert rgb.shape == (CHANNELS, 3)

            # Post processing

            cmax = rgb.max(axis=0).max(axis=0)
            if cmax > 1: # Avoid divide by 0
                maxes = maxes[1:] + [cmax]

                if silent and self.sound_start_callback:
                    self.loop.create_task(self.sound_start_callback())

                silent = False
            else:
                silent = True

            cmax = max(maxes)

            if self.settings["smoothing"] > 0:
                rgb_last -= cmax * self.CHUNK / self.RATE / self.settings["smoothing"]
                rgb_last = np.where(rgb_last < 0, 0, rgb_last)

                rgb = np.where(rgb > rgb_last, rgb, rgb_last)
                wobble = np.where(rgb[:, 0] < rgb_last[:, 0], wobble_last, wobble)

            assert wobble.shape == (CHANNELS,)
            rgb_last = rgb.copy()
            wobble_last = wobble

            # Format to send

            rgb *= 255 / cmax * self.settings["brightness"]

            minimum = self.hex_to_rgb(self.settings["minimum"])
            white = self.hex_to_rgb(self.settings["white"])

            minimum = minimum * white // 255

            wobble = np.where(rgb[:, 0] <= minimum[0], False, wobble)
            rgb = np.where(rgb < minimum, minimum, rgb)

            rgb = rgb.astype(np.int32)

            # Broadcast
            while not self.new_data and self.running:
                m = self.settings["wobble"] * 0.5
                wobble_mult = np.where(wobble, math.sin(time.monotonic() * 2 * math.pi * 16) * m + 1 - m, 1).reshape(CHANNELS, 1)

                def write():
                    try:
                        self.arduino.write(bytes([42]))
                        self.arduino.write((rgb * wobble_mult).reshape(CHANNELS * 3).astype(np.int32).tolist())

                        if self.arduino.read() != bytes([42]):
                            return 1
                        return 2

                    except serial.serialutil.SerialException:
                        return 0

                result = await self.loop.run_in_executor(None, write)
                if result == 0:
                    print("Microcontroller disconnected.")
                    await self.connect_to_arduino(print_message=True)
                elif result == 1:
                    print("Invalid confirmation from microcontroller. Waiting 5 seconds.")
                    await asyncio.sleep(5)

                if not self.running:
                    break

                await asyncio.sleep(0)

        if self.arduino:
            def close():
                self.arduino.write(bytes([42]))
                self.arduino.write(bytes([0] * (CHANNELS * 3)))
                self.arduino.read()
                self.arduino.close()

            await self.loop.run_in_executor(None, close)

    def hex_to_rgb(self, hex):
        hex = hex[1:]
        hex = np.array([int(num, 16) for num in hex])
        hex = hex.reshape(3, 2)
        return hex[:, 0] * 16 + hex[:, 1]

    def callback(self, in_data, frame_count, time_info, status_flags):
        self.data = in_data
        self.new_data = True

        return in_data, pyaudio.paContinue

    # This function takes input from the console so its good practice to run it on the main thread
    async def run(self, additional_message=""):
        self.loop = asyncio.get_event_loop()

        # Ask user for input
        print('\nAvailable audio devices:\n')
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            print(f'Device {i + 1}: {info['name']}')

        print('\nSelect input device')
        input_device = await self.input_number(int, 1, self.p.get_device_count()) - 1
        print('Select output device')
        output_device = await self.input_number(int, 1, self.p.get_device_count()) - 1

        print("\nAvailable ports:\n")

        ports = serial.tools.list_ports.comports()
        for i, port in enumerate(ports, 1):
            print(f"{i}: {port.device}")

        print("\nSelect port")
        port_index = await self.input_number(int, 1, len(ports)) - 1
        self.port = ports[port_index]

        # Open stream

        try:
            self.stream = await self.loop.run_in_executor(None, lambda:
                            self.p.open(format=self.p.get_format_from_width(BYTES_PER_SAMPLE),
                                channels=CHANNELS,
                                rate=self.RATE,
                                input=True,
                                output=True,
                                frames_per_buffer=self.CHUNK,
                                input_device_index=input_device,
                                output_device_index=output_device,
                                stream_callback=self.callback))
        except:
            print("Could not open stream.")
            self.p.terminate()

        self.loop.create_task(self.relay())

        print(f'Relaying. Input setting=value to change settings. Input "exit" to exit. { additional_message }')

        while self.running:
            a = await self.input()
            if a == "exit":
                self.running = False
            elif a in self.commands:
                self.loop.create_task(self.commands[a]())
            else:
                a = a.split("=")
                if len(a) == 2 and a[0] in self.settings:
                    try:
                        if type(self.settings[a[0]]) == int:
                            self.settings[a[0]] = int(a[1])
                        elif type(self.settings[a[0]]) == float:
                            self.settings[a[0]] = float(a[1])
                        elif type(self.settings[a[0]]) == str:
                            self.settings[a[0]] = a[1]

                        print(f"Setting { a[0] } set to { self.settings[a[0]] }")

                        if self.setting_changed_callback:
                            await self.setting_changed_callback()

                    except ValueError:
                        print("Number could not be parsed.")

                elif len(a) == 2:
                    print("Setting nonexistent.")
                else:
                    print("Input not recognized.")

        print('Stopping.')

        self.stream.close()
        self.p.terminate()

        if self.exit_callback:
            await self.exit_callback()
        