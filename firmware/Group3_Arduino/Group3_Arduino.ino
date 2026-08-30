//
// 03 June 2026
// Wong YC
// revision 1
//
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <Arduino_Nesso_N1.h>
#include <Arduino_BMI270_BMM150.h>
#include <M5GFX.h>
#M5GFX display;
#NessoBattery battery;

// Sampling parameters
const int sampleRate = 100;                             // 100 Hz
const unsigned long sampleTime = 1000 / sampleRate;     // 10ms between samples

// Data collection variables
unsigned long lastSample = 0;
// Timer variables
unsigned long lastTime = 0;
unsigned long timerDelay = 30000;
uint16_t chargeLevel = 0;
//
int count = 0; // set up counter to display battery status in the LCD screen
//
bool deviceConnected = false;
bool acclDataValid = false;
bool gyroDataValid = false;
// bool connected_before = false;
//BLE server name
// change this to our group name & your name e.g. G2_Alice
// this the name being broadcast by the sensor
// Try and keep to within 9 characters
#define bleServerName "241504D"

//
// BLE Service and Characteristic UUIDs (you can use custom 128-bit UUIDs)
// can use uuidgenerator.net to generate UUIDs
// You must use a unique UUID
#define SERVICE_UUID              "bdc766fc-7eee-417f-bbe0-2e71a8a2bf70"   // Example service (could be a custom one)
//
// variables to hold the accelerometer and gyroscope data
//
float accX, accY, accZ;
float gyrX, gyrY, gyrZ;
//
// Set up bluetooth charateristics and descriptor for
// the data from the accelerometer, gyroscope and both
// The characteristics UUID must be unique!
//
BLECharacteristic BMI270_accelCharacteristics("cba1d466-344c-4be3-ab3f-189f80dd7518", BLECharacteristic::PROPERTY_NOTIFY);
BLEDescriptor BMI270_accelDescriptor(BLEUUID((uint16_t)0x2A58)); //0x2902
BLECharacteristic BMI270_gyroCharacteristics("19a36902-0338-413f-90e5-b429fcd37164", BLECharacteristic::PROPERTY_NOTIFY);
BLEDescriptor BMI270_gyroDescriptor(BLEUUID((uint16_t)0x2A58)); //0x2902
BLECharacteristic BMI270_accelngyroCharacteristics("f509416c-3c4b-401e-a768-b25a9e621a91", BLECharacteristic::PROPERTY_NOTIFY);
BLEDescriptor BMI270_accelngyroDescriptor(BLEUUID((uint16_t)0x2A58)); //0x2902

//Setup callbacks onConnect and onDisconnect
class MyServerCallbacks: public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
  };
  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
  }
};
//
void setup() {
  // turn on battery charging! 
  battery.begin();
  battery.enableCharge();
  //
  Serial.begin(9600);
  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB port only
  }
  Serial.println("Loading Program");
  // Set up the LCD screen
  display.begin();
  display.setRotation(1); // Landscape mode
  display.setTextColor(TFT_WHITE, TFT_BLACK);
  display.fillScreen(TFT_GREEN);
  display.setTextSize(1.5);
  display.setTextDatum(MC_DATUM);
  display.drawString("- Initializing IMU...", display.width() / 2, display.height() / 2);
   // Initialize the IMU sensor (BMI270)
   
  if (!IMU.begin()) {
    Serial.println("Failed to initialize BMI270 IMU!");
    while (1);
  }
  Serial.println("BMI270 IMU initialized.");
  // get battery power level to show on the LCD screen
  chargeLevel = battery.getChargeLevel();
  Serial.print("Charge Level %: ");
  Serial.println(chargeLevel);
  delay(3000);
  // Set up the LCD display
  display.fillScreen(TFT_BLACK);
  display.setTextSize(1.5);
  display.setTextDatum(TL_DATUM);
  display.drawString("Battery ",5,95);
  display.setCursor(78,95);
  display.printf("%d", chargeLevel);
  display.drawString("%",110,95);
  display.drawString(bleServerName,130,95);
  display.drawString("Waiting for BLE connection",5,110);
  //
  display.drawString("- Accl Gyro Data:", 5, 5);
  display.drawString("- X:", 5, 30);
  display.drawString("- Y:", 5, 45);
  display.drawString("- Z:", 5, 60);
  display.drawString("g", 100, 30);
  display.drawString("g", 100, 45);
  display.drawString("g", 100, 60);
  //
  display.drawString("d/s",185,30);
  display.drawString("d/s",185,45);
  display.drawString("d/s",185,60);
  // Create the BLE Device
  BLEDevice::init(bleServerName);

  // Create the BLE Server
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create the BLE Service
  BLEService *bmiService = pServer->createService(SERVICE_UUID);
  //
  
  // Create BLE Characteristics and Create a BLE Descriptor
  bmiService->addCharacteristic(&BMI270_accelCharacteristics);
  BMI270_accelDescriptor.setValue("Accelerometer");
  BMI270_accelCharacteristics.addDescriptor(&BMI270_accelDescriptor);
  //
  bmiService->addCharacteristic(&BMI270_gyroCharacteristics);
  BMI270_gyroDescriptor.setValue("Gyroscope");
  BMI270_gyroCharacteristics.addDescriptor(&BMI270_gyroDescriptor);
  //
  bmiService->addCharacteristic(&BMI270_accelngyroCharacteristics);
  BMI270_accelngyroDescriptor.setValue("AccelerometerAndGyroscope");
  BMI270_accelngyroCharacteristics.addDescriptor(&BMI270_accelngyroDescriptor);
  // Start the service
  bmiService->start();
  //
  //
  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pServer->getAdvertising()->start();
  Serial.println("Waiting a client connection to notify...");
} // !-- end of setup function

void loop() {
  // put your main code here, to run repeatedly:
  unsigned long currentTime = millis();
  
  if (deviceConnected) {
    Serial.println("Device connected");                  
    
    if (currentTime - lastSample >= sampleTime) {
      //Serial.print(currentTime); Serial.print(" ");
      //Serial.print(lastSample); Serial.print(" ");
      //Serial.print(sampleTime); Serial.println("*");

      if (IMU.accelerationAvailable()) {
          IMU.readAcceleration(accX, accY, accZ);
          acclDataValid = true;
        }
      if (IMU.gyroscopeAvailable()) {
            IMU.readGyroscope(gyrX, gyrY, gyrZ);
          gyroDataValid = true;
          }
      if ((acclDataValid && gyroDataValid) == true) {
        Serial.print("Accel (g): ");
        Serial.print(accX); Serial.print(", ");
        Serial.print(accY); Serial.print(", ");
        Serial.println(accZ);
        Serial.print("Gyro (dps): ");
        Serial.print(gyrX); Serial.print(", ");
        Serial.print(gyrY); Serial.print(", ");
        Serial.println(gyrZ);
// Prepare data for BLE (as comma-separated string)
        char accelBuffer[20];
        char gyroBuffer[20];
        char allBuffer[40];
        snprintf(accelBuffer, sizeof(accelBuffer), "%.2f,%.2f,%.2f", accX, accY, accZ); // if only need accelerometer
        snprintf(gyroBuffer, sizeof(gyroBuffer), "%.2f,%.2f,%.2f", gyrX, gyrY, gyrZ); // if only need gyroscope
        snprintf(allBuffer, sizeof(allBuffer), "%.2f,%.2f,%.2f,%.2f,%.2f,%.2f", accX, accY, accZ, gyrX, gyrY, gyrZ);
  // send the data out throught bluetooth
  // you can choose to send only the accelerometer, or gyroscope data separately
  // using e.g., BMI270_accelCharateriscs... or BMI270_gyroCharacteristics defined
  // earlier in the program
  // the code below will send out both the accelerometer and gyroscope data
    BMI270_accelngyroCharacteristics.setValue(allBuffer);
    BMI270_accelngyroCharacteristics.notify();
    // Update display with current values
      display.fillRect(45, 30, 50, 45, TFT_BLACK);
      display.setTextColor(TFT_GREEN, TFT_BLACK);
      display.setTextSize(1.5);
      display.setCursor(40, 30);
      display.printf("%+.3f", accX);
      display.setCursor(40, 45);
      display.printf("%+.3f", accY);
      display.setCursor(40, 60);
      display.printf("%+.3f", accZ);
    // display the angle
      display.setCursor(120,30);
      display.printf("%+.1f",gyrX);
      display.setCursor(120,45);
      display.printf("%+.1f",gyrY);
      display.setCursor(120,60);
      display.printf("%+.1f",gyrZ);
    // update the battery level
    // get battery power level to show on the LCD screen
      chargeLevel = battery.getChargeLevel();
      display.setCursor(78,95);
      display.printf("%d", chargeLevel);
    } // data valid
    lastSample = currentTime;
    count++;
    // This part will update the battery status on the LCD every 500 passes in the cycle
    if (count > 10000 || count == 1) {
        chargeLevel = battery.getChargeLevel();
        Serial.print("Charge Level %: ");
        Serial.println(chargeLevel);
        //display.drawString("Battery Level ",5,95);
        display.setCursor(78,95);
        display.printf("%d", chargeLevel);
        //display.drawString(" %",155,95);
        //display.drawString("BLE connected             ",5,110);
        count = 0;
    }
  }
    
  } else {
    Serial.println("BLE x disconnected");
    display.drawString("Waiting for BLE connection",5,110);
  }
  
}