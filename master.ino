#include <FastLED.h>

#define FAKE_EMITTER 1

// config
// bus config
const byte interruptPin = 2;  //@todo rename
#ifdef FAKE_EMITTER
const byte signalEmitterPin = 7;  // fake stuff
int makeFakePulse = -1;
#endif
const byte numSensors = 3;
const long syncPulseLength = 200;       // how long is the sync pulse
int silentZoneLength = 500;             // how long sensors wait after sync pulse
int sensorFrameLength = 500;            // how long each sensor has to emit its pulse
int ignorePulsesFromSensorsFor = 3000;  // how long to ignore sensors for after they start emitting
// leds config
#define NUM_LEDS 100
#define DATA_PIN 6
// end config

// global vars
// bus vars
long endSyncPulseAt = 0;
bool syncPulseStarted = false;
bool listening = false;
int sensorPulses[numSensors];
long lastSensorPulse[numSensors] = {};  // all init to 0
unsigned long lastBusCycleAt = 0;
unsigned int busCycleInterval = syncPulseLength + silentZoneLength + (numSensors * sensorFrameLength);
// leds vars
CRGB leds[NUM_LEDS];
byte ledsTarget[NUM_LEDS];
byte ledsBrightness[NUM_LEDS];
unsigned long ledsTargetDurationStart[NUM_LEDS];
unsigned int ledsTargetDuration[NUM_LEDS];
const byte numSections = 4;
// led sections {startIdx, endIdex, isOn}
byte ledSections[numSections][4] = {
  { 0, 9, 0 },    // P0
  { 10, 19, 0 },  // F0
  { 20, 29, 0 },  // P1
  { 30, 39, 0 }   // F1
};
long ledSectionsTurnOff[numSections] = {};

// end global vars


void setup() {
  Serial.begin(57600);

  // bus: INPUT by default
  pinMode(interruptPin, INPUT_PULLUP);
#ifdef FAKE_EMITTER
  pinMode(signalEmitterPin, INPUT);  // fake stuff
#endif
  attachInterrupt(digitalPinToInterrupt(interruptPin), onSensorSignal, FALLING);

  // leds
  FastLED.addLeds<WS2811, DATA_PIN>(leds, NUM_LEDS);
  FastLED.setBrightness(20);
  FastLED.setCorrection(Typical8mmPixel);
  // init all leds at FairyLight color at 0 brightness (off)
  for (int i = 0; i < NUM_LEDS; i++) {
    leds[i] = CRGB::FairyLight;
    leds[i].nscale8(0);
    ledsBrightness[i] = 0;  // init actual brightness
    ledsTarget[i] = 0;      // init target brightness
  }
  FastLED.show();
}

void loop() {
  unsigned long currentMillis = millis();

  // leds business
  for (int i = 0; i < NUM_LEDS; i++) {
    if (ledsTarget[i] != ledsBrightness[i] && currentMillis >= ledsTargetDurationStart[i]) {

      int animationTime = currentMillis - ledsTargetDurationStart[i];  // how many millis into the animation
      int animationDuration = ledsTargetDuration[i];

      float bri;
      if (ledsTarget[i] > ledsBrightness[i]) {
        // dimming up
        bri = animationTime * (255.0 / animationDuration);
        if (bri > 255) {
          bri = 255;
        }
      } else {
        // dimming down
        bri = 255 - (animationTime * (255.0 / animationDuration));
        if (bri < 0) {
          bri = 0;
        }
      }

      ledsBrightness[i] = static_cast<int>(bri);
      leds[i] = CRGB::FairyLight;
      leds[i].nscale8(ledsBrightness[i]);
    }
  }
  FastLED.show();

  // bus business
  if (currentMillis - lastBusCycleAt > busCycleInterval) {
    lastBusCycleAt = currentMillis;
    // -> START BUS CYCLE
    listening = false;

    // reset sensor data
    for (int i = 0; i < numSensors; i++) {
      sensorPulses[i] = 0;
    }

    // 1. Sync pulse
    // 1.1 Master becomes output
    pinMode(interruptPin, OUTPUT);
    // 1.2 Start sync pulse
    digitalWrite(interruptPin, LOW);

    syncPulseStarted = true;
  }

  if (syncPulseStarted && currentMillis - lastBusCycleAt > syncPulseLength) {
    syncPulseStarted = false;

    // 1.3 End sync pulse
    digitalWrite(interruptPin, HIGH);

    // 1.4 Master back to input
    pinMode(interruptPin, INPUT_PULLUP);

    listening = true;
  }

  // any section should turn off ?
  for (int i = 0; i < numSections; i++) {
    if (ledSectionsTurnOff[i] > 0 && currentMillis > ledSectionsTurnOff[i]) {
      transitionSegmentRnd(ledSections[i][0], ledSections[i][1], 0, 1000);
      ledSectionsTurnOff[i] = 0;
    }
  }

  for (int i = 0; i < numSensors; i++) {
    if (sensorPulses[i] > 0) {
      onSensorTrigger(i);
      sensorPulses[i] = 0;
    }
  }

#ifdef FAKE_EMITTER
  if (Serial.available() > 0) {
    // read the incoming byte:
    int incomingByte = Serial.read();

    if (incomingByte == 49) {  // 1
      makeFakePulse = 1;
    }
    if (incomingByte == 50) {  // 2
      makeFakePulse = 2;
    }

    // say what you got:
    //Serial.print("I received: ");
    //Serial.println(incomingByte, DEC);
  }
  // fake stuff
  int relativeMillis = currentMillis - lastBusCycleAt;
  if (makeFakePulse > 0 && relativeMillis > syncPulseLength + silentZoneLength + (sensorFrameLength * (makeFakePulse - 1)) + 1 && relativeMillis < syncPulseLength + silentZoneLength + (sensorFrameLength * makeFakePulse)) {
    //Serial.println(makeFakePulse);
    //Serial.println(makeFakePulse - 1);
    makeFakePulse = 0;
    //Serial.print("signal @");

    // Serial.print("mil-lastBusCycleAt=");
    // Serial.println(currentMillis - lastBusCycleAt);
    // Serial.print("lastBusCycleAt=");
    // Serial.println(lastBusCycleAt);
    emitSignal();
  }
#endif
}

// called when a sensor triggers (debounced, called only once, not repeatedly like onSensorSignal)
void onSensorTrigger(int sensorIdx) {
  Serial.print("onSensorTrigger@");
  Serial.println(sensorIdx);
  if (sensorIdx == 0) {
    lightupSection(0);
  }
  if (sensorIdx == 1 || sensorIdx == 2) {
    lightupSection(1);
  }
}

void lightupSection(int sectionIdx) {
  transitionSegmentRnd(ledSections[sectionIdx][0], ledSections[sectionIdx][1], 255, 1000);
  ledSectionsTurnOff[sectionIdx] = millis() + 5000;
}

// leds utils
void transitionPixel(int idx, int brightness, int duration, int offset = 0) {
  ledsTarget[idx] = brightness;
  ledsTargetDurationStart[idx] = millis() + offset;
  ledsTargetDuration[idx] = duration;
}
void transitionSegment(int startIdx, int endIdx, int brightness, int duration) {
  for (int i = startIdx; i <= endIdx; i++) {
    transitionPixel(i, brightness, duration);
  }
}
void transitionSegmentRnd(int startIdx, int endIdx, int brightness, int duration) {
  for (int i = startIdx; i <= endIdx; i++) {
    transitionPixel(i, brightness, duration, random(0, 1000));
  }
}
void walkSegment(int startIdx, int endIdx, int brightness, int duration) {
  for (int i = startIdx; i <= endIdx; i++) {
    transitionPixel(i, brightness, duration, i * 60);
  }
}

// bus: when sensors send a signal (ISR)
void onSensorSignal() {
  if (!listening) return;
  unsigned long currentMillis = millis();

  long sensorsStartAt = lastBusCycleAt + syncPulseLength + silentZoneLength;
  int offset = currentMillis - sensorsStartAt;
  int idx = offsetToIdx(offset, sensorFrameLength * numSensors, numSensors);

  if (lastSensorPulse[idx] > 0 && currentMillis - lastSensorPulse[idx] < ignorePulsesFromSensorsFor) {
    return;
  }

  sensorPulses[idx] = 1;
}
int offsetToIdx(int offset, int range, int num) {
  return floor(((float)offset / range) * num);
}

#ifdef FAKE_EMITTER
void emitSignal() {
  pinMode(signalEmitterPin, OUTPUT);
  digitalWrite(signalEmitterPin, LOW);
  delay(1);
  digitalWrite(signalEmitterPin, HIGH);
  pinMode(signalEmitterPin, INPUT);
}
#endif
