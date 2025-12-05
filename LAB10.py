import umqtt.robust as umqtt
from network import WLAN
import time
from machine import Pin, ADC, Timer, RTC


try:
    from temperature_upb2 import TemperaturereadingMessage
except ImportError:
    print("Error: temperature_upb2.py not found")
    raise


BROKER_IP = '172.20.10.4'
TOPIC = 'temp/pico'

# PUBLISHER: Set OUTPUT_PIN = None, PUB_IDENT = 'pico_pub_1' (or 'pico_pub_2')
# SUBSCRIBER: Set OUTPUT_PIN = 'LED', PUB_IDENT = None
OUTPUT_PIN = 'LED'
PUB_IDENT = None

SSID = 'LimaPhone'
PASSWORD = '12345678'
PORT = 1883
TEMP_THRESHOLD = 25.0
PUBLISHER_TIMEOUT = 600

# Validate configuration
if OUTPUT_PIN is None and PUB_IDENT is None:
    print("Error: Both OUTPUT_PIN and PUB_IDENT are None. Set one to configure mode.")
    raise SystemExit

if OUTPUT_PIN is not None and PUB_IDENT is not None:
    print("Error: Both OUTPUT_PIN and PUB_IDENT are set. Only one should be set.")
    raise SystemExit

# Track publisher temperatures and timestamps
publisher_data = {}

# Connect to WiFi
wifi = WLAN(WLAN.IF_STA)
wifi.active(True)
wifi.connect(SSID, PASSWORD)

while not wifi.isconnected():
    time.sleep(1)

print('Connected to WiFi')

# Initialize RTC
rtc = RTC()

# Read temperature from internal sensor
def read_temp():
    temp_sensor = ADC(4)
    value = temp_sensor.read_u16()
    voltage = value * (3.3 / 2 ** 16)
    return 27 - (voltage - 0.706) / 0.001721

# Calculate average temperature from active publishers (within last 10 minutes)
def calculate_average_temp():
    current_time = time.ticks_ms() // 1000
    active_temps = []
   
    # Clean up old publishers (memory constraint requirement)
    to_remove = []
    for pub_ident, data in publisher_data.items():
        if current_time - data['timestamp'] > PUBLISHER_TIMEOUT:
            to_remove.append(pub_ident)
        else:
            active_temps.append(data['temp'])
   
    # Remove stale publishers to free memory
    for pub_ident in to_remove:
        del publisher_data[pub_ident]
   
    return sum(active_temps) / len(active_temps) if active_temps else None

# Callback when subscriber receives a message
def subscriber_callback(topic, message):
    try:
        # Deserialize protobuf message
        temp_reading = TemperaturereadingMessage()
        temp_reading.parse(message)
       
        # Extract values using ._value attribute
        pub_ident = temp_reading.publisher_id._value
        temperature = temp_reading.temperature._value
       
        seconds = temp_reading.time._value

        print(f'Received: {pub_ident} - {temperature:.2f}°C at {seconds:02d}')
       
        # Store publisher data
        publisher_data[pub_ident] = {
            'temp': temperature,
            'timestamp': seconds
        }
       
        # Calculate average and control output
        avg_temp = calculate_average_temp()
       
        if avg_temp is not None:
            if avg_temp > TEMP_THRESHOLD:
                output_device.value(1)
                print(f'LED ON - Avg temp: {avg_temp:.2f}°C > {TEMP_THRESHOLD}°C')
            else:
                output_device.value(0)
                print(f'LED OFF - Avg temp: {avg_temp:.2f}°C <= {TEMP_THRESHOLD}°C')
   
    except Exception as e:
        print(f'Error parsing message: {e}')

# Timer callback for publisher - sends temperature reading
def publisher_timer_callback(t):
    try:
        
        temp_reading = TemperaturereadingMessage()
        temperature = read_temp()
       
        # Get current time from RTC

        seconds = time.time()
        temp_reading.time = seconds
        temp_reading.temperature = temperature
        temp_reading.publisher_id = PUB_IDENT
       
        # Serialize and publish
        serialized = temp_reading.serialize()
        mqtt.publish(TOPIC.encode(), serialized)
       
        print(f'Published: {PUB_IDENT} - {temperature:.2f}°C at {seconds:02d}')
   
    except Exception as e:
        print(f'Error publishing: {e}')

# Timer callback for subscriber
def subscriber_timer_callback(t):
    mqtt.check_msg()

# Determine mode based on configuration
is_publisher = (PUB_IDENT is not None and OUTPUT_PIN is None)

# Initialize output pin for subscriber mode
if not is_publisher:
    output_device = Pin(OUTPUT_PIN, Pin.OUT)
    output_device.value(0)

# Connect to MQTT broker
mqtt = umqtt.MQTTClient(
    client_id=(PUB_IDENT if is_publisher else 'subscriber').encode(),
    server=BROKER_IP.encode(),
    port=PORT,
    keepalive=7000
)

mqtt.connect()
print('Connected to MQTT broker')

# Setup timer based on mode
timer = Timer()

if is_publisher:
    print(f'Running as PUBLISHER: {PUB_IDENT}')
    timer.init(freq=0.5, mode=Timer.PERIODIC, callback=publisher_timer_callback)
else:
    print(f'Running as SUBSCRIBER on pin: {OUTPUT_PIN}')
    mqtt.set_callback(subscriber_callback)
    mqtt.subscribe(TOPIC.encode())
    timer.init(freq=2, mode=Timer.PERIODIC, callback=subscriber_timer_callback)
