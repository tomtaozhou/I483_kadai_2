from machine import I2C, Pin
import time
import network
from umqtt.robust import MQTTClient

from scd41 import SCD41
from dps310 import DPS310
from rpr0521rs import RPR0521RS
from bh1750 import BH1750


STUDENT     = "s2510085"
WIFI_SSID   = "JAISTALL"
WIFI_PASS   = ""
MQTT_BROKER = "150.65.230.59"
MQTT_PORT   = 1883
MQTT_CLIENT_ID = STUDENT + "-pico"

CO2_ALERT_TOPIC = "i483/actuators/{}/co2_threshold_crossed".format(STUDENT).encode()

INTERVAL_S = 10


led = Pin(6, Pin.OUT)
led.off()
co2_over_threshold = False


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    time.sleep(1)
    wlan.active(True)
    time.sleep(1)
    if not wlan.isconnected():
        print("Connecting WiFi:", WIFI_SSID)
        wlan.connect(WIFI_SSID, WIFI_PASS)
        for _ in range(40):
            if wlan.isconnected():
                break
            time.sleep_ms(500)
    if wlan.isconnected():
        print("WiFi OK, IP:", wlan.ifconfig()[0])
    else:
        print("WiFi connect failed")
    return wlan


def on_message(topic, msg):
    global co2_over_threshold
    print("[MQTT] {} -> {}".format(topic.decode(), msg.decode()))
    if topic == CO2_ALERT_TOPIC:
        val = msg.decode().strip().lower()
        co2_over_threshold = val in ("yes", "true", "1", "on")


def connect_mqtt():
    try:
        client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=60)
        client.set_callback(on_message)
        client.connect()
        client.subscribe(CO2_ALERT_TOPIC)
        print("MQTT OK, subscribed:", CO2_ALERT_TOPIC.decode())
        return client
    except Exception as e:
        print("MQTT connect failed:", e)
        return None


def publish(client, sensor, data_type, value):
    if client is None:
        return
    topic   = "i483/sensors/{}/{}/{}".format(STUDENT, sensor, data_type)
    payload = "{:.2f}".format(value)
    try:
        client.publish(topic.encode(), payload.encode())
    except Exception as e:
        print("publish failed:", e)


connect_wifi()
mqtt = connect_mqtt()

i2c = I2C(0, sda=Pin(1), scl=Pin(0), freq=100000)


def safe_init(name, fn):
    try:
        return fn()
    except Exception as e:
        print("{} init failed: {}".format(name, e))
        return None


scd41  = safe_init("SCD41",   lambda: SCD41(i2c))
dps310 = safe_init("DPS310",  lambda: DPS310(i2c))
rpr    = safe_init("RPR0521", lambda: RPR0521RS(i2c))
bh     = safe_init("BH1750",  lambda: BH1750(i2c))

time.sleep(1)

if rpr and bh:
    try:
        ref = bh.read_lux()
        if ref > 5:
            d0, d1 = rpr.read_raw()
            if d0 == 0 and d1 == 0:
                rpr.reinit()
                time.sleep_ms(600)
            rpr.calibrate_with(ref)
    except Exception:
        pass


last_scd41 = None

while True:
    if mqtt:
        try:
            mqtt.check_msg()
        except Exception as e:
            print("MQTT check_msg error:", e)

    if scd41:
        try:
            scd41.wake_up()
            scd41.measure_single_shot()
            time.sleep(5)
            co2, scd_t, scd_h = scd41.read_measurement()
            last_scd41 = (co2, scd_t, scd_h)
        except Exception:
            pass

        if last_scd41 is not None:
            co2, scd_t, scd_h = last_scd41
            print("SCD41 co2: {} ppm, temperature: {:.2f} C, humidity: {:.2f} %RH".format(
                co2, scd_t, scd_h))
            publish(mqtt, "SCD41", "co2",         co2)
            publish(mqtt, "SCD41", "temperature", scd_t)
            publish(mqtt, "SCD41", "humidity",    scd_h)

    if dps310:
        try:
            dps_t, dps_p = dps310.read()
            print("DPS310 temperature: {:.2f} C, air_pressure: {:.2f} hPa".format(
                dps_t, dps_p / 100.0))
            publish(mqtt, "DPS310", "temperature",  dps_t)
            publish(mqtt, "DPS310", "air_pressure", dps_p / 100.0)
        except Exception as e:
            print("DPS310 error:", e)

    if rpr:
        try:
            d0, d1 = rpr.read_raw()
            if d0 == 0 and d1 == 0:
                rpr.reinit()
                time.sleep_ms(600)
                d0, d1 = rpr.read_raw()
            vis_lux = rpr.read_lux()
            print("RPR0521 illumination: {:.2f} lx, infrared_illumination: {} count".format(
                vis_lux, d1))
            publish(mqtt, "RPR0521", "illumination",          vis_lux)
            publish(mqtt, "RPR0521", "infrared_illumination", float(d1))
        except Exception as e:
            print("RPR0521 error:", e)

    if bh:
        try:
            bh_lux = bh.read_lux()
            print("BH1750 illumination: {:.2f} lx".format(bh_lux))
            publish(mqtt, "BH1750", "illumination", bh_lux)
        except Exception as e:
            print("BH1750 error:", e)

    if co2_over_threshold:
        for _ in range(3):
            led.on()
            time.sleep_ms(200)
            led.off()
            time.sleep_ms(200)
    else:
        led.off()

    print()
    time.sleep(INTERVAL_S)