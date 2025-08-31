# This test routine should light up the left channel led strip red, and the right channel led strip green. It is useful for finding the color ordering of your particular led strip

import serial
import serial.tools.list_ports

print("Available ports: ")

ports = serial.tools.list_ports.comports()
for i, port in enumerate(ports, 1):
    print(f"{i}: {port.device}")

print("Select port")
port = ports[int(input()) - 1]

arduino = serial.Serial(port=port.device, baudrate=115200, timeout=1)

arduino.write(bytes([42, 20, 0, 0, 0, 20, 0]))

if arduino.read() != bytes([42]):
    print("Invalid confirmation from arduino")
else:
    print("Done")
