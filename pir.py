import RPi.GPIO as GPIO
import time


SENSOR_PIN = 23
 
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_PIN, GPIO.IN)
 
def my_callback(channel):
    # Here, alternatively, an application / command etc. can be started.
    print('There was a movement!')
 
try:
    GPIO.add_event_detect(SENSOR_PIN , GPIO.FALLING, callback=my_callback)
    while True:
        if GPIO.input(SENSOR_PIN):
            print('aha!')
        time.sleep(0.3)
except KeyboardInterrupt:
    print("Finish...")
GPIO.cleanup()
