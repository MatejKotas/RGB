# This test routine should flash up the left channel led strip red, and the right channel led strip green. Then both led strips should turn blue. It is useful for finding the color ordering of your particular led strip.

import serial
import serial.tools.list_ports
import time

print("Available ports: ")

ports = serial.tools.list_ports.comports()
for i, port in enumerate(ports, 1):
    print(f"{i}: {port.device}")

print("Select port")
port = ports[int(input()) - 1]

arduino = serial.Serial(port=port.device, baudrate=115200, timeout=1)

time.sleep(1)

if int(arduino.read()[0]) != 42:
    print("Invalid confirmation from arduino")

arduino.read()
arduino.read()
arduino.read()

arr = [42, 255, 0, 0, 0, 255, 0, 0, 0, 255]

arduino.write(bytes(arr))
time.sleep(1)

if arduino.read() != bytes([42]):
    print("Invalid confirmation from arduino")
else:
    print("Done")
