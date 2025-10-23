#include <Arduino.h>
#include <FastLED.h>
#include <EEPROM.h>

// Modify these according to your setup
#define NUM_LEDS 300
#define DATA_PIN_LEFT 3
#define DATA_PIN_RIGHT 4
#define PROTOCOL WS2812B
#define COLOR_ORDER GBR

#define disconnect_delay 100;
#define save_delay 1000 * 60 * 2;

CRGB ambient_color;
unsigned long connection_timeout;
bool connected = false;
unsigned long save_timer;
bool new_settings = false;

// Define the arrays of leds
CRGB leds[NUM_LEDS];

#define brightness 64

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(1000);

  FastLED.addLeds<PROTOCOL, DATA_PIN_LEFT, COLOR_ORDER>(leds, NUM_LEDS);
  FastLED.addLeds<PROTOCOL, DATA_PIN_RIGHT, COLOR_ORDER>(leds, NUM_LEDS);

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

  ambient_color = readEEPROM();

  colorFill(ambient_color, ambient_color);

  Serial.write(42);
  Serial.write(ambient_color.r);
  Serial.write(ambient_color.g);
  Serial.write(ambient_color.b); 
}

void loop() {
  unsigned long current_time = millis();
  if (new_settings && save_timer < current_time) {
    saveEEPROM(ambient_color);
    new_settings = false;
  }
  if (connected && connection_timeout < current_time) {
    connected = false;

    colorFill(ambient_color, ambient_color);
  }

  if (Serial.available()) {
    if (Serial.read() == 42) {

      // Recieve colors
      CRGB c_left = CRGB(helper(), helper(), helper());
      CRGB c_right = CRGB(helper(), helper(), helper());
      CRGB new_ambient_color = CRGB(helper(), helper(), helper());

      // Set recieved color
      colorFill(c_left, c_right);

      // Send confirmation
      Serial.write(42);

      // Possibly start timer to save ambient color
      if (!colorEquals(ambient_color, new_ambient_color)) {
        ambient_color = new_ambient_color;

        save_timer = millis() + save_delay;
        new_settings = true;
      }

      // Update connection status
      connection_timeout = millis() + disconnect_delay;
      connected = true;
    }
  }
}

int helper() {
  while (!Serial.available()) {}

  return Serial.read();
}

void colorFill(CRGB left, CRGB right) {
  for (int i = 0; i < NUM_LEDS; i++) {
    leds[i] = left;
  }
  FastLED[0].showLeds(brightness);

  for (int i = 0; i < NUM_LEDS; i++) {
    leds[i] = right;
  }

  FastLED[1].showLeds(brightness);
  delay(1); // FastLED causes Serial data corruption
}

bool colorEquals(CRGB c1, CRGB c2) {
  return (c1.r == c2.r && c1.g == c2.g && c1.b == c2.b);
}

CRGB readEEPROM() {
  return CRGB(EEPROM.read(0), EEPROM.read(1), EEPROM.read(2));
}

void saveEEPROM(CRGB color) {
  if (!colorEquals(readEEPROM(), color)) {
    EEPROM.write(0, color.r);
    EEPROM.write(1, color.g);
    EEPROM.write(2, color.b);
  }
}
