import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
from time import sleep, perf_counter # Import the sleep function from the time module

pin=18

#GPIO.setwarnings(False) # Ignore warning for now
GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW) # Set pin 8 to be an output pin and set initial value to low (off)

def millis():
	return int(perf_counter()*1000)

try:
	
	while True: # Run forever
		
		# sync pulse
		GPIO.output(pin, GPIO.HIGH)
		sleep(0.03)
		GPIO.output(pin, GPIO.LOW)
		read_start = millis()
		
		# switch to input
		GPIO.setup(pin, GPIO.IN)
		
		## simple blocking version
		# # wait for pin to go HIGH
		# while True:
			# if GPIO.input(pin):
				# break
		# # pin went to HIGH
		# signal_start = millis()
		# print('its HIGH!!')
		
		# # wait for pin to go LOW
		# while True:
			# if not GPIO.input(pin):
				# break
		# # pin is back to LOW
		# signal_end = millis()
		# print('back to LOW')
		
		# signal_started_after = signal_start - read_start
		# signal_duration = signal_end - signal_start
		# print(f"Signal started after {signal_started_after}, duration: {signal_duration}")
		
		phase_duration = millis() - read_start
		
		wire_val = GPIO.LOW
		prev_wire_val = GPIO.LOW
		signal_start = -1
		signals = []
		#all_vals = []
		iters=0
		while phase_duration < 150:
			wire_val = GPIO.input(pin)
			#if wire_val>0:
			#	all_vals.append((phase_duration,wire_val))
			if prev_wire_val==GPIO.LOW and wire_val==GPIO.HIGH:
				# RISING
				signal_start = phase_duration
			if prev_wire_val==GPIO.HIGH and wire_val==GPIO.LOW:
				# FALLING
				if signal_start==-1:
					print('false fall', iters)
				signals.append({"start": signal_start, "end": phase_duration})
				signal_start = -1
			
			prev_wire_val = wire_val
			phase_duration = millis() - read_start
			iters+=1
		print('signals:', iters, signals)
		#print('all_vals', all_vals)
		GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
		
		
		#sleep(1) # Sleep for 1 second
		
except KeyboardInterrupt:
	GPIO.cleanup()
