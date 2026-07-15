const int ecgPin = 36;
const int buzzerPin = 23;
const int loPlusPin = 2;
const int loMinusPin = 4;

int threshold = 2500;
unsigned long lastBeatTime = 0;
float bpm = 0;
float lastBpm = 0;
bool beatDetected = false;

void setup() {
  Serial.begin(115200);
  pinMode(buzzerPin, OUTPUT);
  pinMode(loPlusPin, INPUT);
  pinMode(loMinusPin, INPUT);
  }

void triggerRapidBuzz() {
  for (int i = 0; i < 5; i++) {
    digitalWrite(buzzerPin, HIGH);
    delay(50);
    digitalWrite(buzzerPin, LOW);
    delay(50);  
    }
  }

void loop() {
  if (digitalRead(loPlusPin) == HIGH || digitalRead(loMinusPin) == HIGH) {
    Serial.println("Sensor electrodes disconnected.");
    digitalWrite(buzzerPin, LOW);
    delay(500);
    return;  
    }
  
  int ecgValue = analogRead(ecgPin);
  
  if (ecgValue > threshold && !beatDetected && (millis() - lastBeatTime > 250)) {
    unsigned long delta = millis() - lastBeatTime;
    lastBeatTime = millis();
    bpm = 60000.0 / delta;
    Serial.print("Current BPM: ");
    Serial.println(bpm);
    if (lastBpm > 0 && abs(bpm - lastBpm) > 20) {
      triggerRapidBuzz();
      }        
    lastBpm = bpm;
    beatDetected = true;  
    }
  }
