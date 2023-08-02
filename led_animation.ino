#include <FastLED.h>
#define NUM_LEDS 100
#define DATA_PIN 6

CRGB leds[NUM_LEDS];
byte ledsTarget[NUM_LEDS];
byte ledsBrightness[NUM_LEDS];
unsigned long ledsTargetDurationStart[NUM_LEDS];
unsigned int ledsTargetDuration[NUM_LEDS];

// simulation (fake stuff)
int target = 255;

void setup() {
  Serial.begin(9600);

  Serial.println("start");

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

  delay(1000);
}

void loop() {
  unsigned long currentMillis = millis();

  EVERY_N_SECONDS(3) {
    if (target == 255) {
      walkSegment(0, 10, target, 400);
    } else {
      transitionSegmentRnd(0, 10, target, 1500);
    }
    target = target == 255 ? 0 : 255;
  }

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
}

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
