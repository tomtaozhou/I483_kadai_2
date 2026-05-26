from machine import Pin
import time

led = Pin(6, Pin.OUT)
for _ in range(5):
    led.on()
    time.sleep(0.5)
    led.off()
    time.sleep(0.5)
print("LED test done")