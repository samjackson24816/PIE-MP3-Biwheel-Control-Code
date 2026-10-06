#include <Wire.h>
#include <Adafruit_MotorShield.h>

// Create the motor shield object with the default I2C address
Adafruit_MotorShield AFMS = Adafruit_MotorShield(); 

// Connect motors to M1 and M2
Adafruit_DCMotor *leftMotor = AFMS.getMotor(1);
Adafruit_DCMotor *rightMotor = AFMS.getMotor(2);

void setup() {
  Serial.begin(9600);
  Serial.println("Continuous Low-Speed Motor Test");

  // Initialize the motor shield
  if (!AFMS.begin()) {
    Serial.println("Could not find Motor Shield. Check wiring!");
    while (1);
  }
  Serial.println("Motor Shield found.");

  // Set initial low speed (0 to 255 scale; 75 is a slow, safe crawling speed)
  leftMotor->setSpeed(75);
  rightMotor->setSpeed(75);

  // Start both motors moving forward continuously
  leftMotor->run(FORWARD);
  rightMotor->run(FORWARD);
}

void loop() {
  // Motors will run continuously at low speed; 
  // you can add sensor reads or debugging here later.
}