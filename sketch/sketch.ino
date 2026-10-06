#include <Wire.h>
#include <Adafruit_MotorShield.h>
#include "Arduino_RouterBridge.h"

// Create the motor shield object with the default I2C address
Adafruit_MotorShield AFMS = Adafruit_MotorShield(); 

// Connect motors to M1 and M2
Adafruit_DCMotor *leftMotor = AFMS.getMotor(1);
Adafruit_DCMotor *rightMotor = AFMS.getMotor(2);

// ==========================================
// CODE-WIDE CONFIGURATION PARAMETERS
// ==========================================
// Set to -1 if a motor is wired backwards physically
const int LEFT_MOTOR_DIR = -1;
const int RIGHT_MOTOR_DIR = 1; 

void onScan() {
  Serial.println("RouterBridge method called: SCAN (Turning in circles)");
  int lSpeed = 100 * LEFT_MOTOR_DIR;
  int rSpeed = -100 * RIGHT_MOTOR_DIR; // Opposite directions for rotation

  leftMotor->setSpeed(abs(lSpeed));
  rightMotor->setSpeed(abs(rSpeed));
  leftMotor->run(lSpeed >= 0 ? FORWARD : BACKWARD);
  rightMotor->run(rSpeed >= 0 ? FORWARD : BACKWARD);
}

void onHunt(float delta) {
  Serial.print("RouterBridge method called: HUNT with delta = ");
  Serial.println(delta);

  int baseSpeed = 75;
  int lSpeed = (baseSpeed + (int)delta) * LEFT_MOTOR_DIR;
  int rSpeed = (baseSpeed - (int)delta) * RIGHT_MOTOR_DIR;

  leftMotor->setSpeed(constrain(abs(lSpeed), 0, 255));
  rightMotor->setSpeed(constrain(abs(rSpeed), 0, 255));

  leftMotor->run(lSpeed >= 0 ? FORWARD : BACKWARD);
  rightMotor->run(rSpeed >= 0 ? FORWARD : BACKWARD);
}

void onStop() {
  Serial.println("RouterBridge method called: STOP");
  leftMotor->setSpeed(0);
  rightMotor->setSpeed(0);
  leftMotor->run(RELEASE);
  rightMotor->run(RELEASE);
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
  onStop();

  // Provide methods for Python MPU
  Bridge.provide("scan", onScan);
  Bridge.provide("hunt", onHunt);
  Bridge.provide("stop", onStop);
}

void loop() {
  delay(100);
}
