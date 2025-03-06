#include "wifi_manager.h"

void initWifiManager() {
    WiFiManager wifiManager;

    if (!wifiManager.autoConnect("AUTOPOTS", "galaquente")) {
        Serial.println("Failed to connect and hit timeout");
        // Restart ESP32
        ESP.restart();
      }
    
      // Connected successfully
      Serial.println("WiFi Connected!");
      Serial.print("IP Address: ");
      Serial.println(WiFi.localIP());
}