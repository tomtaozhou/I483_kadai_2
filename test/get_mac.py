import network

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
mac = wlan.config('mac')
print("MAC:", ':'.join('{:02x}'.format(b) for b in mac))