#include <Wire.h>
#include <Adafruit_MotorShield.h>
#include "Arduino_RouterBridge.h"

// Create the motor shield object with the default I2C address
Adafruit_MotorShield AFMS = Adafruit_MotorShield(); 

// Connect motors to M1 and M2
Adafruit_DCMotor *leftMotor = AFMS.getMotor(1);
Adafruit_DCMotor *rightMotor = AFMS.getMotor(2);

void onScan() {
  Serial.println("RouterBridge method called: SCAN (Turning in circles)");
  // Spin motors in opposite directions to rotate in place (scan)
  leftMotor->setSpeed(100);
  rightMotor->setSpeed(100);
  leftMotor->run(FORWARD);
  rightMotor->run(BACKWARD);
}

void onHunt(float delta) {
  Serial.print("RouterBridge method called: HUNT with delta = ");
  Serial.println(delta);

  int baseSpeed = 75;
  int leftSpeed = baseSpeed + (int)delta;
  int rightSpeed = baseSpeed - (int)delta;

  // Set motor speeds (using absolute value for speed magnitude)
  leftMotor->setSpeed(constrain(abs(leftSpeed), 0, 255));
  rightMotor->setSpeed(constrain(abs(rightSpeed), 0, 255));

  // Set motor directions (FORWARD if speed >= 0, BACKWARD if speed < 0)
  leftMotor->run(leftSpeed >= 0 ? FORWARD : BACKWARD);
  rightMotor->run(rightSpeed >= 0 ? FORWARD : BACKWARD);
}

void setup() {
  Serial.begin(9600);
  Serial.println("Biwheel Control - STM32 Initialized with Arduino_RouterBridge");

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

  // Provide methods so Python MPU can call them via Bridge.notify / Bridge.call
  Bridge.provide("scan", onScan);
  Bridge.provide("hunt", onHunt);
}

void loop() {
  delay(100);
}
