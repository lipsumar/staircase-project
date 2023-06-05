import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color
from MovingAverageFilter import MovingAverageFilter
import time
import threading
import random 
import pytweening
 
#### RPi.GPIO setup (HC-SR04)
#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)
#set GPIO Pins
GPIO_TRIGGER = 23
GPIO_ECHO = 24
#set GPIO direction (IN / OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)
 
 
#### ledstrip config
LED_COUNT = 50        # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
# LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 50  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
 
 
 
 
def distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)
 
    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)
 
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()
 
    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
 
    return distance
 
def blackout():
    global strip_model
    for i, _ in enumerate(strip_model):
        strip_model[i]['target'] = 0
 
 
def all_color(strip, color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()
 
def translate(value, leftMin, leftMax, rightMin, rightMax):
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin
 
    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)
 
    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)
 
def transition_pixel_old(idx, val):
    global strip_model
    start_brightness = strip_model[idx][1]  # Initial brightness
    end_brightness = val #100  # Target brightness
    duration = 0.1  # Transition duration in seconds
 
    start_time = time.time()
    end_time = start_time + duration
 
    while time.time() < end_time:
        elapsed_time = time.time() - start_time
        progress = elapsed_time / duration
        brightness = pytweening.easeInOutSine(progress) * (end_brightness - start_brightness) + start_brightness
 
        strip_model[idx][0] = int(brightness)
        time.sleep(0.05)  # Delay between updates
 
    strip_model[idx][0] = end_brightness  # Ensure the final brightness is set

def transition_pixel(idx, target):
    global strip_model
    strip_model[idx]['target'] = target
    strip_model[idx]['transition'] = {
        'duration': 0.1,
    }

 
# Create NeoPixel object with appropriate configuration.
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
# Intialize the library (must be called once before other functions).
strip.begin()
sensor_dist = 200

strip_model = [{'actual':-1, 'target': 0, 'transition': None} for _ in range(strip.numPixels())]
# Example state
# pix = {
#     'actual': 0, 
#     'wanted': 255, 
#     'transition': {
#         'start_time': None,
#         'end_time': None,
#         'duration': None,
#         'start_brightness': None,
#         'end_brightness': None
#     }
# }
 
# This thread is responsible for reading the sensor
# and store it in sensor_dist
def sensor_thread_fn():
    global sensor_dist
    avg_filter = MovingAverageFilter(window_size=10, first_value=200)
    while True:
        dist = distance()
        if dist > 200:
            dist = 200
        dist_smooth = avg_filter.get_smoothed_value()
        avg_filter.add_value(dist)
        sensor_dist = dist_smooth
        time.sleep(0.1)
 
 
def debug_thread_fn():
    global sensor_dist
    while True:
        time.sleep(1)
        print(sensor_dist)
 
 
# This thread is responsible to drive the lights
# based on strip_model
def strip_thread_fn():
    global strip_model, strip
 
    def update_strip():
        updated_any = False
        for i, pix in enumerate(strip_model):
            if pix['actual'] == pix['target']:
                continue
            
            if pix['transition'] is not None:
                now = time.time()
                transition = pix['transition']

                # transition is brand new, initialize it
                if transition['start_time'] is None:
                    transition['start_time'] = now
                    transition['end_time'] = transition['start_time'] + transition['duration']
                    transition['start_brightness'] = pix['actual']
                    transition['end_brightness'] = pix['target']
                    strip_model[i]['transition'] = transition
                
                # transition is ongoing
                if transition['start_time'] is not None:
                    elapsed_time = now - transition['start_time']
                    progress = elapsed_time / transition['duration']
                    brightness = pytweening.easeInOutSine(progress) * (transition['end_brightness'] - transition['start_brightness']) + transition['start_brightness']
                    strip.setPixelColor(i, Color(int(brightness), int(brightness), int(brightness)))
                    strip_model[i]['actual'] = int(brightness)

                    # transition is over
                    if now > transition['end_time']:
                        strip_model[i]['transition'] = None
                        strip.setPixelColor(i, Color(pix['target'], pix['target'], pix['target']))
                        strip_model[i]['actual'] = pix['target']

            updated_any = True
        if updated_any:
            strip.show()
            #print('update strip', strip_model)
 
    while True:
        update_strip()
 
def controller_thread_fn():
    global strip_model, sensor_dist
 
    blackout()
    while True:
        for i, pix in enumerate(strip_model):
            transition_pixel(i, 120)
            time.sleep(0.1)
            # transition_pixel(i-1, 120)
            # transition_pixel(i+1, 120)
            # time.sleep(1)
        blackout()
        time.sleep(1)
 
 
if __name__ == '__main__':
    #sensor_thread = threading.Thread(target=sensor_thread_fn)
    debug_thread = threading.Thread(target=debug_thread_fn)
    strip_thread = threading.Thread(target=strip_thread_fn)
    controller_thread = threading.Thread(target=controller_thread_fn)
    #sensor_thread.start()
    #debug_thread.start()
    strip_thread.start()
    controller_thread.start()
 