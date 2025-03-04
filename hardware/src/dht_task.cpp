#include "dht_task.h"

DHT dht(DHTPIN, DHTTYPE);
TaskHandle_t DhtTaskHandle = NULL;

void initDhtTask() {
    dht.begin();
    xTaskCreate(DhtTask, "Temperature Read", 2048, NULL, 1, &DhtTaskHandle);
}

void DhtTask(void *pvParameters) {
    for (;;) {
        // Read sensor data
        float temp = dht.readTemperature();
        float hum = dht.readHumidity();

        // Try to access protected data
        if (xSemaphoreTake(sensorData.mutex, portMAX_DELAY) == pdTRUE) {

            if (!isnan(temp) && !isnan(hum)) {
                sensorData.temperature = temp;
                sensorData.humidity = hum;
            }

            xSemaphoreGive(sensorData.mutex);
        }

        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}