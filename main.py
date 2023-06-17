from rpi_ws281x import PixelStrip, Color
import RPi.GPIO as GPIO
import time
import threading
import random
import pytweening


WIRE_PIN = 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(WIRE_PIN, GPIO.OUT)
# GPIO.setup(24, GPIO.IN)

# ledstrip config
LED_COUNT = 50        # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
# LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 50  # Set to 0 for darkest and 255 for brightest
# True to invert the signal (when using NPN transistor level shift)
LED_INVERT = False
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53


def blackout():
    global strip_model
    for i, _ in enumerate(strip_model):
        strip_model[i]['target'] = 0


def all_color(strip, color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()


def transition_pixel(idx, target, duration=0.5, delay=0.0, next=None):
    global strip_model

    if idx < 0 or idx >= len(strip_model):
        return

    strip_model[idx]['target'] = target
    strip_model[idx]['transition'] = {
        'duration': duration,
        'delay': delay,
        'next': next
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


def ripple(center, length, target):
    off_transition = {'target': 0, 'delay': 2, 'duration': 0.2}
    transition_pixel(center, target, duration=0.2, next=off_transition)
    for i in range(1, length // 2):
        transition_pixel(center - i, target, delay=0.1*i,
                         duration=0.2, next=off_transition)
        transition_pixel(center + i, target, delay=0.1*i,
                         duration=0.2, next=off_transition)


# Create NeoPixel object with appropriate configuration.
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
# Intialize the library (must be called once before other functions).
strip.begin()
sensor_dist = 200

strip_model = [{'actual': -1, 'target': 0, 'transition': None}
               for _ in range(strip.numPixels())]
# Example state
# pix = {
#     'actual': 0,
#     'wanted': 255,
#     'transition': {
#         'start_time': None,
#         'end_time': None,
#         'duration': None,
#         'start_brightness': None,
#         'end_brightness': None,
#         'delay': None,
#         'next': //transition_pixel args
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
                    transition['start_time'] = now + transition['delay']
                    transition['end_time'] = transition['start_time'] + \
                        transition['duration']
                    transition['start_brightness'] = pix['actual']
                    transition['end_brightness'] = pix['target']
                    strip_model[i]['transition'] = transition

                # transition is ongoing
                if transition['start_time'] is not None:
                    next_trans = None
                    # transition is over
                    if now > transition['end_time']:
                        if 'next' in transition:
                            next_trans = transition['next']
                        strip_model[i]['transition'] = None
                        brightness = pix['target']
                    elif transition['start_time'] > now:
                        # transition not started yet
                        continue
                    else:
                        elapsed_time = now - transition['start_time']
                        progress = elapsed_time / transition['duration']
                        brightness = pytweening.easeInOutSine(
                            progress) * (transition['end_brightness'] - transition['start_brightness']) + transition['start_brightness']

                    strip.setPixelColor(
                        i, Color(int(brightness), int(brightness), int(brightness)))
                    strip_model[i]['actual'] = int(brightness)

                    if next_trans:
                        transition_pixel(i, **next_trans)

            else:
                strip.setPixelColor(
                    i, Color(pix['target'], pix['target'], pix['target']))
                strip_model[i]['actual'] = pix['target']

            updated_any = True
        if updated_any:
            strip.show()
            # print('update strip', strip_model)

    while True:
        update_strip()
        # time.sleep(0.2)


def controller_thread_fn():
    global strip_model, sensor_dist

    def on_detect(pin):
        if pin == 23:
            led_id = random.randint(1, LED_COUNT/2)
        else:
            led_id = random.randint(LED_COUNT/2, LED_COUNT)
        ripple(led_id, 15, 120)

    # GPIO.add_event_detect(SENSOR_PIN , GPIO.RISING, callback=on_detect)
    GPIO.add_event_detect(24, GPIO.RISING, callback=on_detect)

    blackout()

    # start animation
    for i, pix in enumerate(strip_model):
        transition_pixel(i, 120, delay=i*0.05, duration=0.1,
                         next={'target': 0, 'delay': 0.4})

    # transition_pixel(3, 255)
    while True:
        # for i, pix in enumerate(strip_model):
        #    transition_pixel(i, 120, next={'target':0, 'delay':1})
        #    time.sleep(0.02)
        #    # transition_pixel(i-1, 120)
        #    # transition_pixel(i+1, 120)
        #    # time.sleep(1)
        # time.sleep(2)
        # blackout()
        time.sleep(1)


def controller_thread2_fn():
    blackout()

    GPIO.setup(WIRE_PIN, GPIO.OUT)

    start_time = time.perf_counter()
    sync_pulse_started = False
    sync_pulse_started_at = None
    sync_pulse_ended_at = None

    # sync pulse
    while True:
        elapsed_time_mic = (time.perf_counter() - start_time) * 1_000_000

        # send sync pulse
        if not sync_pulse_started:
            sync_pulse_started_at = elapsed_time_mic
            GPIO.output(WIRE_PIN, GPIO.HIGH)
            sync_pulse_started = True
            continue

        # sync pulse is over
        if elapsed_time_mic - sync_pulse_started_at > 25:
            sync_pulse_ended_at = elapsed_time_mic
            GPIO.output(WIRE_PIN, GPIO.LOW)
            break

    print('sync pulse length', sync_pulse_ended_at - sync_pulse_started_at)

    time.sleep(1)

    """
    els = []
    while True:
        elapsed_milli = (time.perf_counter() - start_time)*1_000_000
        #print(elapsed_milli)
        els.append(elapsed_milli)
        
        #if(len(els)==3):
        #    GPIO.output(WIRE_PIN, GPIO.HIGH)
        #if(len(els)==4):
        #    GPIO.output(WIRE_PIN, GPIO.LOW)
        if(len(els)==3):
            i = GPIO.input(WIRE_PIN)
        if(len(els)==5):
            i = GPIO.input(WIRE_PIN)
        
        if(len(els)>20):
            break;
    print(els)
    """

    """
    while True:
        # print('sync pulse')
        GPIO.setup(WIRE_PIN, GPIO.OUT)
        sync_pulse_start_at = time.perf_counter()
        # emit sync signal of 25 microseconds
        GPIO.output(WIRE_PIN, GPIO.HIGH)
        time.sleep(0.0000025)
        GPIO.output(WIRE_PIN, GPIO.LOW)
        sync_pulse_end_at = time.perf_counter()

        pulse_length_mic = (sync_pulse_end_at - sync_pulse_start_at)*1_000_000
        print('pulse_length_mic', pulse_length_mic)

        # set wire to input
        GPIO.setup(WIRE_PIN, GPIO.IN)

        # wait for 10 microseconds
        time.sleep(0.00001)

        loops = 0
        pulses = []
        while True:
            loops += 1
            time_since_sync_end_mic = (
                time.perf_counter() - sync_pulse_end_at) * 1_000_000

            # read wire pin
            if GPIO.input(WIRE_PIN) == GPIO.HIGH:
                # print('pulse after', time_since_sync_end_mic)
                pulses.append(time_since_sync_end_mic)

            # wait for 1 microsecond
            time.sleep(0.000001)

            # exit 80 microseconds after sync pulse
            if time_since_sync_end_mic > 80:
                break
        print(loops, 'loops', pulses)
    """


if __name__ == '__main__':
    # sensor_thread = threading.Thread(target=sensor_thread_fn)
    debug_thread = threading.Thread(target=debug_thread_fn)
    strip_thread = threading.Thread(target=strip_thread_fn)
    controller_thread = threading.Thread(target=controller_thread2_fn)
    # sensor_thread.start()
    # debug_thread.start()
    strip_thread.start()
    controller_thread.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        blackout()
        GPIO.cleanup()
