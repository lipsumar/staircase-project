from rpi_ws281x import PixelStrip, Color
import RPi.GPIO as GPIO
import time
import threading
import random 
import pytweening
 

SENSOR_PIN = 23 
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_PIN, GPIO.IN)
 
#### ledstrip config
LED_COUNT = 50        # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
# LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 50  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
 
 
 
def blackout():
    global strip_model
    for i, _ in enumerate(strip_model):
        strip_model[i]['target'] = 0
 
 
def all_color(strip, color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show() 

def transition_pixel(idx, target):
    global strip_model

    if idx < 0 or idx >= len(strip_model):
        return

    strip_model[idx]['target'] = target
    strip_model[idx]['transition'] = {
        'duration': 0.5,
    }

def lightup_segment(start, end, target):
    global strip_model
    print('segment', start, end, target)
    for i in range(start, end):
        print('trans', i)
        transition_pixel(i, target)

def lightup_segment_from_center(center, length, target):
    global strip_model
    start = center - length // 2
    end = center + length // 2
    lightup_segment(start, end, target)

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
                if 'start_time' not in transition:
                    transition['duration'] = transition['duration'] if transition['duration'] else 1.0
                    transition['start_time'] = now
                    transition['end_time'] = transition['start_time'] + transition['duration']
                    transition['start_brightness'] = pix['actual']
                    transition['end_brightness'] = pix['target']
                    strip_model[i]['transition'] = transition
                
                # transition is ongoing
                if transition['start_time'] is not None:
                    # transition is over
                    if now > transition['end_time']:
                        strip_model[i]['transition'] = None
                        brightness = pix['target']
                    else:
                        elapsed_time = now - transition['start_time']
                        progress = elapsed_time / transition['duration']
                        brightness = pytweening.easeInOutSine(progress) * (transition['end_brightness'] - transition['start_brightness']) + transition['start_brightness']
                    
                    strip.setPixelColor(i, Color(int(brightness), int(brightness), int(brightness)))
                    strip_model[i]['actual'] = int(brightness)
                    
            else:
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
 
    def on_detect(pin):
        led_id = random.randint(1,50)
        lightup_segment_from_center(led_id, 6, 120)
        
        
    GPIO.add_event_detect(SENSOR_PIN , GPIO.FALLING, callback=on_detect)
        
         
    blackout()
    #transition_pixel(3, 255)
    while True:
        #for i, pix in enumerate(strip_model):
        #    transition_pixel(i, 120)
        #    time.sleep(0.02)
        #    # transition_pixel(i-1, 120)
        #    # transition_pixel(i+1, 120)
        #    # time.sleep(1)
        #time.sleep(2)
        #blackout()
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
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        blackout()
        GPIO.cleanup()
 
