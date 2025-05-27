#include <WiFi.h>
#include <WiFiManager.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>

// Configurações iniciais (podem ser sobrescritas pelo WiFiManager)
char serverUrl[40] = "http://192.168.15.119:5000";
char userEmail[40] = "rafael@gmail.com"; // Valor padrão

// Pino do sensor e variáveis
const int moistureSensorPin = 34;
unsigned long lastTime = 0;
const long timerDelay = 1000;

// Armazenamento persistente
Preferences preferences;
int poteId = -1;

// WiFiManager
WiFiManager wifiManager;

int readNutrientLevel() {
    // Implemente sua lógica real do sensor aqui
    return random(0, 101);
}

void saveConfigCallback() {
    Serial.println("Configurações salvas via WiFiManager");
}

int readMoistureSensor() {                           
    int sensorValue = analogRead(moistureSensorPin);
    
    int dryValue = 4095;   // Valor quando completamente seco (ar)
    int wetValue = 400;   // Valor quando completamente molhado (em água)
    
    sensorValue = constrain(sensorValue, wetValue, dryValue);
    
    int moisture = map(sensorValue, dryValue, wetValue, 0, 100);
    
    // Debug (opcional)
    Serial.print("Leitura bruta: ");
    Serial.print(sensorValue);
    Serial.print(" - Umidade: ");
    Serial.print(moisture);
    Serial.println("%");
    
    return moisture;
}

void createNewPote() {
    HTTPClient http;
    String url = String(serverUrl) + "/new_pote";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    DynamicJsonDocument doc(256);
    doc["name"] = "Novo Pote";
    doc["especie"] = "Planta Padrão";
    doc["email"] = userEmail;

    String jsonStr;
    serializeJson(doc, jsonStr);

    int httpCode = http.POST(jsonStr);

    if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        DynamicJsonDocument respDoc(256);
        deserializeJson(respDoc, payload);
        
        if (respDoc.containsKey("pote_id")) {
        poteId = respDoc["pote_id"];
        preferences.putInt("poteId", poteId);
        Serial.print("Novo pote criado! ID: ");
        Serial.println(poteId);
        }
    } else {
        Serial.print("Erro ao criar pote: ");
        Serial.println(httpCode);
    }
    http.end();
}

void sendSensorData() {
    HTTPClient http;
    String url = String(serverUrl) + "/get_sensor_data";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    DynamicJsonDocument doc(256);
    doc["id"] = poteId;
    doc["umidade"] = readMoistureSensor();
    doc["nutrientes"] = readNutrientLevel();
    doc["email"] = userEmail;

    String jsonStr;
    serializeJson(doc, jsonStr);

    int httpCode = http.POST(jsonStr);

    if (httpCode == HTTP_CODE_OK) {
        String response = http.getString();
        Serial.println("Dados enviados com sucesso!");
        Serial.println(response);
    } else {
        Serial.print("Erro no envio: ");
        Serial.println(httpCode);
        
        // Se erro for 404 (pote não encontrado), tenta obter novo ID
        if (httpCode == 404) {
        poteId = -1;
        preferences.remove("poteId");
        }
    }
    http.end();
}

void getPoteIdFromServer() {
    HTTPClient http;
    String url = String(serverUrl) + "/get_pote_id/" + String(userEmail);

    http.begin(url);
    int httpCode = http.GET();

    if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        DynamicJsonDocument doc(256);
        deserializeJson(doc, payload);
        
        if (doc.containsKey("pote_id")) {
        poteId = doc["pote_id"];
        preferences.putInt("poteId", poteId);
        Serial.print("Pote ID obtido: ");
        Serial.println(poteId);
        } else {
        Serial.println("Nenhum pote encontrado - Criando novo...");
        createNewPote();
        }
    } else {
        Serial.print("Erro ao obter poteID: ");
        Serial.println(httpCode);
    }
    http.end();
}

void resetAllSettings() {
    // Limpa as configurações WiFi
    wifiManager.resetSettings();
    
    // Limpa nossas preferências personalizadas
    preferences.begin("poteConfig", false);
    preferences.clear();
    preferences.end();
    
    Serial.println("Todas as configurações foram resetadas!");
    delay(1000);
    
    // Reinicia o ESP
    ESP.restart();
  }
