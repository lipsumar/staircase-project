
const int led = 1;
const int sensor = 2;
const int wire = 0;

byte wire_val = LOW;
byte prev_wire_val = LOW;

int wire_self_adress = 1;
int wire_max_adress = 6;
// adress 0 => 0-10 mic
// adress 1 => 10-20 mic
// adress 2 => 20-30 mic
// adress 3 => 30-40 mic
// adress 4 => 40-50 mic
// adress 5 => 50-60 mic

void setup() {
  pinMode(led, OUTPUT);    // initalize LED as an output
  pinMode(sensor, INPUT);  // initialize sensor as an input
  pinMode(wire, INPUT);
  
  prev_wire_val = digitalRead(wire);
  //Serial.begin(9600);        // initialize serial
  digitalWrite(led, LOW);
  delay(500);
  digitalWrite(led, HIGH);
  delay(500);
  digitalWrite(led, LOW);
  delay(500);
  digitalWrite(led, HIGH);
  delay(500);
  digitalWrite(led, LOW);
  delay(500);
  digitalWrite(led, HIGH);
  delay(500);
  digitalWrite(led, LOW);
  delay(500);

  //attachInterrupt(0, onWireRise, RISING);
  //attachInterrupt(0, onWireFall, FALLING);
}

void loop() {
  static uint32_t pulse_start = 0;
  static boolean pulse_started = LOW;
  /*
  digitalWrite(0, HIGH);
  digitalWrite(led, HIGH);
  delay(5000);
  digitalWrite(0, LOW);
  digitalWrite(led, LOW);
  delay(5000);
  */
  int mil = millis();
  
  wire_val = digitalRead(wire);


  if(wire_val==HIGH && prev_wire_val==LOW){
    // RISE
    pulse_start = mil;
    pulse_started = HIGH;
    digitalWrite(led, HIGH);
  }
  
  if(wire_val==LOW && prev_wire_val==HIGH){
    // FALL
    digitalWrite(led, LOW);
    if(pulse_started == HIGH){
      pulse_started = LOW;
      int pulse_duration = mil - pulse_start;
      pulse_start = 0;
      if(pulse_duration > 20) {
        //double_flash();
        // SYNC PULSE DETECTED
        int start_after = 1 + (wire_self_adress * 10);
        int max_time = 1 + (wire_max_adress * 10);

        int sensor_val = digitalRead(sensor);
        
        delay(start_after);
        if(sensor_val == HIGH){
          pinMode(wire, OUTPUT);
          digitalWrite(wire, HIGH);
          delay(5);
          digitalWrite(wire, LOW);
          pinMode(wire, INPUT);
        } else {
          delay(5);
        }
        delay(max_time - start_after);
      }
    }
  }

  prev_wire_val = wire_val;
}
