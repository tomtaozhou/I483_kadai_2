import network
import time

wlan = network.WLAN(network.STA_IF)

wlan.active(False)
time.sleep(1)
wlan.active(True)
time.sleep(1)

print("Scanning nearby WiFi networks:")
networks = wlan.scan()
for n in networks:
    ssid = n[0].decode() if n[0] else "<hidden>"
    rssi = n[3]
    print("  {} (signal {} dBm)".format(ssid, rssi))

print("\nConnecting to JAISTALL...")
wlan.connect("JAISTALL", "")

for i in range(30):
    if wlan.isconnected():
        print("WiFi OK")
        print("IP:", wlan.ifconfig()[0])
        print("Gateway:", wlan.ifconfig()[2])
        print("DNS:", wlan.ifconfig()[3])
        break
    print("waiting... {}s, status={}".format(i, wlan.status()))
    time.sleep(1)
else:
    print("\nWiFi connection failed")
    print("Final status:", wlan.status())