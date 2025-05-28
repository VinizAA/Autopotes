#include <Arduino.h>
#include "main.hpp"
#include <WebServer.h>

#define VALVE_PIN 4

WebServer server(80);

void setup() {
  pinMode(VALVE_PIN, OUTPUT);

  Serial.begin(9600);
  
  // Carrega configurações salvas
  preferences.begin("poteConfig", false);
  poteId = preferences.getInt("poteId", -1);
  preferences.getString("userEmail", userEmail, 40);
  preferences.getString("serverUrl", serverUrl, 40);

  // Parâmetros configuráveis
  WiFiManagerParameter custom_email("email", "Email do usuário", userEmail, 40);
  WiFiManagerParameter custom_server("server", "URL do servidor", serverUrl, 40);
  
  wifiManager.addParameter(&custom_email);
  wifiManager.addParameter(&custom_server);
  
  // Configurações do WiFiManager
  wifiManager.setDebugOutput(true);
  wifiManager.setConfigPortalTimeout(180);
  wifiManager.setSaveParamsCallback(saveConfigCallback);

  if (!wifiManager.autoConnect("SmartPoteAP")) {
    Serial.println("Falha na conexão");
    delay(3000);
    ESP.restart();
  }

  // Atualiza valores se foram alterados
  if (strcmp(userEmail, custom_email.getValue()) != 0) {
    strncpy(userEmail, custom_email.getValue(), 40);
    preferences.putString("userEmail", userEmail);
    poteId = -1; // Força obter novo poteId para o novo email
  }
  
  if (strcmp(serverUrl, custom_server.getValue()) != 0) {
    strncpy(serverUrl, custom_server.getValue(), 40);
    preferences.putString("serverUrl", serverUrl);
  }

  Serial.println("\nConfigurações carregadas:");
  Serial.print("Email: "); Serial.println(userEmail);
  Serial.print("Servidor: "); Serial.println(serverUrl);
  Serial.print("Pote ID: "); Serial.println(poteId);

  if (poteId == -1) {
    getPoteIdFromServer();
  }

  server.on("/reset", HTTP_GET, []() {
    server.send(200, "text/plain", "Resetando configurações...");
    resetAllSettings();
  });
  
  server.begin();
}


void loop() {
  server.handleClient();

  if ((millis() - lastTime) > timerDelay) {
    if (WiFi.status() == WL_CONNECTED) {
      if (poteId == -1) {
        getPoteIdFromServer();
      } else {
        sendSensorData();
      }
    } else {
      Serial.println("WiFi desconectado - Tentando reconectar...");
      WiFi.reconnect();
    }
    lastTime = millis();
  }

  int curr_moisture = readMoistureSensor();
  if (curr_moisture < 20 && digitalRead(VALVE_PIN) == LOW) digitalWrite(VALVE_PIN, HIGH);
  else {
    if (digitalRead(VALVE_PIN) == HIGH) digitalWrite(VALVE_PIN, LOW);
  }
}