from kafka import KafkaConsumer, KafkaProducer
from collections import deque
import time
import threading

STUDENT = "s2510085"
KAFKA_BROKER = "150.65.230.59:9092"

TOPIC_BH_IN   = "i483-sensors-{}-BH1750-illumination".format(STUDENT)
TOPIC_BH_OUT  = "i483-sensors-{}-BH1750-avg-illumination".format(STUDENT)
TOPIC_CO2_IN  = "i483-sensors-{}-SCD41-co2".format(STUDENT)
TOPIC_CO2_OUT = "i483-actuators-{}-co2_threshold-crossed".format(STUDENT)

WINDOW_SECONDS = 5 * 60
PUBLISH_INTERVAL = 30
CO2_THRESHOLD = 700.0


producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: v.encode() if isinstance(v, str) else v,
)


bh_window = deque()


def bh_average_task():
    consumer = KafkaConsumer(
        TOPIC_BH_IN,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset='latest',
        group_id="{}-bh-avg".format(STUDENT),
    )
    print("[BH avg] Consumer started, topic:", TOPIC_BH_IN)

    last_publish = 0
    for msg in consumer:
        try:
            val = float(msg.value.decode())
            now = time.time()
            bh_window.append((now, val))
            while bh_window and bh_window[0][0] < now - WINDOW_SECONDS:
                bh_window.popleft()
            if now - last_publish >= PUBLISH_INTERVAL and len(bh_window) > 0:
                avg = sum(v for _, v in bh_window) / len(bh_window)
                payload = "{:.2f}".format(avg)
                producer.send(TOPIC_BH_OUT, payload)
                producer.flush()
                print("[BH avg] n={} avg={} -> {}".format(
                    len(bh_window), payload, TOPIC_BH_OUT))
                last_publish = now
        except Exception as e:
            print("[BH avg] error:", e)


prev_state = None


def co2_threshold_task():
    global prev_state
    consumer = KafkaConsumer(
        TOPIC_CO2_IN,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset='latest',
        group_id="{}-co2-threshold".format(STUDENT),
    )
    print("[CO2] Consumer started, topic:", TOPIC_CO2_IN)

    for msg in consumer:
        try:
            val = float(msg.value.decode())
            cur_state = "yes" if val > CO2_THRESHOLD else "no"
            if cur_state != prev_state:
                producer.send(TOPIC_CO2_OUT, cur_state)
                producer.flush()
                print("[CO2] {:.2f} -> '{}' -> {}".format(
                    val, cur_state, TOPIC_CO2_OUT))
                prev_state = cur_state
        except Exception as e:
            print("[CO2] error:", e)


if __name__ == "__main__":
    t1 = threading.Thread(target=bh_average_task, daemon=True)
    t2 = threading.Thread(target=co2_threshold_task, daemon=True)
    t1.start()
    t2.start()
    print("Running. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")