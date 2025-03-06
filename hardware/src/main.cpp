#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <WiFiManager.h>
#include "sensor_data.h"
#include "dht_task.h"
#include "display_task.h"
#include "wifi_manager.h"


void setup() {
  Serial.begin(9600);
  
  // Inicializa o WiFiManager
  initWifiManager();
  
  // Semaphore
  sensorData.mutex = xSemaphoreCreateMutex();
  
  // Tasks
  initDhtTask();
  initDisplayTask();
  
  delay(1000);
}

void loop() {
  // Loop vazio pois estamos usando FreeRTOS tasks
}