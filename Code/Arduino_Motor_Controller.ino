/*
 * TRÌNH ĐIỀU KHIỂN LASER - NHẬN TỌA ĐỘ TRỰC TIẾP
 */
#include <AccelStepper.h>
#include <MultiStepper.h>

#define X_STEP_PIN 5
#define X_DIR_PIN 2
#define Y_STEP_PIN 6
#define Y_DIR_PIN 3
#define EN_PIN 8 

AccelStepper stepperX(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
AccelStepper stepperY(AccelStepper::DRIVER, Y_STEP_PIN, Y_DIR_PIN);
MultiStepper steppers; 

long positions[2] = {0, 0}; // [X, Y]
bool isMoving = false;

void setup() {
  Serial.begin(115200);
  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, LOW); 

  stepperX.setMaxSpeed(50.0);      
  stepperY.setMaxSpeed(50.0);      

  steppers.addStepper(stepperX);
  steppers.addStepper(stepperY);

  Serial.println("READY");
}

void loop() {
  // 1. Lắng nghe lệnh từ Python
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    if (cmd == "r" || cmd == "R") {
      // Lệnh về gốc
      positions[0] = 0;
      positions[1] = 0;
      steppers.moveTo(positions);
      isMoving = true;
    } 
    else {
      // Tách chuỗi "X,Y" để lấy tọa độ
      int commaIndex = cmd.indexOf(',');
      if (commaIndex > 0) {
        long targetX = cmd.substring(0, commaIndex).toInt();
        long targetY = cmd.substring(commaIndex + 1).toInt();
        
        positions[0] = targetX;
        positions[1] = targetY;
        steppers.moveTo(positions);
        isMoving = true;
      }
    }
  }

  // 2. Chạy động cơ và báo cáo khi xong
  if (isMoving) {
    if (stepperX.distanceToGo() == 0 && stepperY.distanceToGo() == 0) {
      isMoving = false;
      Serial.println("DONE"); // Báo cho Python biết đã tới đích
    } else {
      steppers.run();
    }
  }
}
