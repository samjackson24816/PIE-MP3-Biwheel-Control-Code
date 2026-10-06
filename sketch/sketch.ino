#include <Wire.h>
#include <Adafruit_MotorShield.h>
#include "Arduino_RouterBridge.h"
#include "Arduino_RPClite.h"

// Create the motor shield object with the default I2C address
Adafruit_MotorShield AFMS = Adafruit_MotorShield(); 

// Connect motors to M1 and M2
Adafruit_DCMotor *leftMotor = AFMS.getMotor(1);
Adafruit_DCMotor *rightMotor = AFMS.getMotor(2);

void onScan() {
  Serial.println("RPC received: scan");
  leftMotor->setSpeed(60);
  rightMotor->setSpeed(60);
  leftMotor->run(FORWARD);
  rightMotor->run(BACKWARD);
}

void onHunt(float delta) {
  Serial.print("RPC received: hunt with delta = ");
  Serial.println(delta);

  int baseSpeed = 75;
  int leftSpeed = constrain(baseSpeed + (int)delta, 0, 255);
  int rightSpeed = constrain(baseSpeed - (int)delta, 0, 255);

  leftMotor->setSpeed(leftSpeed);
  rightMotor->setSpeed(rightSpeed);
  leftMotor->run(FORWARD);
  rightMotor->run(FORWARD);
}

void setup() {
  Serial.begin(9600);
  Serial.println("Biwheel Control - STM32 Initialized with RouterBridge & RPClite");

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

  // Bind RPC functions using Arduino_RPClite
  RPC.bind("scan", onScan);
  RPC.bind("hunt", onHunt);
}

void loop() {
  // Run RPClite to process incoming calls from Python MPU
  RPC.run();
}
