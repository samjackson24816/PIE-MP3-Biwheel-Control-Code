#include <Wire.h>
#include <Adafruit_MotorShield.h>
#include <Bridge.h>

// Create the motor shield object with the default I2C address
Adafruit_MotorShield AFMS = Adafruit_MotorShield(); 

// Connect motors to M1 and M2
Adafruit_DCMotor *leftMotor = AFMS.getMotor(1);
Adafruit_DCMotor *rightMotor = AFMS.getMotor(2);

void setup() {
  Serial.begin(9600);
  Serial.println("Biwheel Control - STM32 Initialized with Bridge");

  // Initialize Bridge communication with Linux MPU
  Bridge.begin();

  // Initialize the motor shield
  if (!AFMS.begin()) {
    Serial.println("Could not find Motor Shield. Check wiring!");
    while (1);
  }
  Serial.println("Motor Shield found.");

  // Set initial stopped state
  leftMotor->setSpeed(0);
  rightMotor->setSpeed(0);
  leftMotor->run(RELEASE);
  rightMotor->run(RELEASE);
}

void loop() {
  char modeBuf[32];
  char deltaBuf[32];

  // Fetch mode and delta from Bridge key-value store updated by Python MPU
  Bridge.get("mode", modeBuf, sizeof(modeBuf));
  Bridge.get("delta", deltaBuf, sizeof(deltaBuf));

  String mode = String(modeBuf);
  mode.trim();
  float delta = String(deltaBuf).toFloat();

  if (mode == "scan") {
    // Turn slowly in circles (one motor forward, one backward)
    leftMotor->setSpeed(60);
    rightMotor->setSpeed(60);
    leftMotor->run(FORWARD);
    rightMotor->run(BACKWARD);
  } 
  else if (mode == "hunt") {
    int baseSpeed = 75;
    int leftSpeed = constrain(baseSpeed + (int)delta, 0, 255);
    int rightSpeed = constrain(baseSpeed - (int)delta, 0, 255);

    leftMotor->setSpeed(leftSpeed);
    rightMotor->setSpeed(rightSpeed);
    leftMotor->run(FORWARD);
    rightMotor->run(FORWARD);
  } 
  else {
    // Default stop if mode not set
    leftMotor->setSpeed(0);
    rightMotor->setSpeed(0);
    leftMotor->run(RELEASE);
    rightMotor->run(RELEASE);
  }

  delay(100); // Check Bridge state periodically
}
