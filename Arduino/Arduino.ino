#include <Arduino.h>
#include <FastLED.h>

// Modify these according to your setup
#define NUM_LEDS 150
#define DATA_PIN_LEFT 3
#define DATA_PIN_RIGHT 10
#define MAX_POWER_MILLIAMPS 2500
#define PROTOCOL WS2812B
#define COLOR_ORDER GBR

// Define the arrays of leds
CRGB leds_left[NUM_LEDS];
CRGB leds_right[NUM_LEDS];

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(1000);

  FastLED.addLeds<PROTOCOL, DATA_PIN_LEFT, COLOR_ORDER>(leds_left, NUM_LEDS);
  FastLED.addLeds<PROTOCOL, DATA_PIN_RIGHT, COLOR_ORDER>(leds_right, NUM_LEDS);

  // You may use this as a refrence of protocols and color orderings
  // ## Clockless types ##

  // FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);  // GRB ordering is assumed
  // FastLED.addLeds<SM16824E, DATA_PIN, RGB>(leds, NUM_LEDS);  // RGB ordering (uses SM16824EController)
  // FastLED.addLeds<SM16703, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<TM1829, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<TM1812, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<TM1809, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<TM1804, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<TM1803, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<UCS1903, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<UCS1903B, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<UCS1904, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<UCS2903, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<WS2812B, DATA_PIN_LEFT, GRB>(leds, NUM_LEDS);    // GRB ordering is typical
  // FastLED.addLeds<WS2852, DATA_PIN, RGB>(leds, NUM_LEDS);  // GRB ordering is typical
  // FastLED.addLeds<WS2812, DATA_PIN, RGB>(leds, NUM_LEDS);  // GRB ordering is typical
  // FastLED.addLeds<GS1903, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<SK6812, DATA_PIN, RGB>(leds, NUM_LEDS);  // GRB ordering is typical
  // FastLED.addLeds<SK6822, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<APA106, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<PL9823, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<SK6822, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<WS2811, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<WS2813, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<APA104, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<WS2811_400, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<GE8822, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<GW6205, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<GW6205_400, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<LPD1886, DATA_PIN, RGB>(leds, NUM_LEDS);
  // FastLED.addLeds<LPD1886_8BIT, DATA_PIN, RGB>(leds, NUM_LEDS);

  FastLED.setMaxPowerInVoltsAndMilliamps(5, MAX_POWER_MILLIAMPS);

  for (int i = 0; i < NUM_LEDS; i++) {
    leds_left[i] = CRGB::Black;
    leds_right[i] = CRGB::Black;
  }

  FastLED.show();
}

void loop() {
  if (helper() == 42) {
    CRGB c_left = CRGB(helper(), helper(), helper());
    CRGB c_right = CRGB(helper(), helper(), helper());

    for (int i = 0; i < NUM_LEDS; i++) {
      leds_left[i] = c_left;
      leds_right[i] = c_right;
    }
    FastLED.show();
    Serial.write(42);
  }
}

uint8_t helper() {
  while (!Serial.available())
    ;
  return Serial.read();
}