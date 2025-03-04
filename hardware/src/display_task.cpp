#include "display_task.h"

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
TaskHandle_t displayTaskHandle = NULL;

void initDisplayTask() {
    // Initialize the OLED display and halt if display fails
    if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
        for(;;);
    }
    display.clearDisplay();

    xTaskCreate(displayTask, "Display Update", 2048, NULL, 1, &displayTaskHandle);
}

void displayTask(void *pvParameters) {
    for (;;) {
        float currentTemp = 0;
        float currentHum = 0;

        // Try to access protected data
        if (xSemaphoreTake(sensorData.mutex, portMAX_DELAY) == pdTRUE) {
            currentTemp = sensorData.temperature;
            currentHum = sensorData.humidity;
     
            xSemaphoreGive(sensorData.mutex);
        }

        // Displays data on OLED
        display.clearDisplay();
        display.setTextSize(1);
        display.setTextColor(SSD1306_WHITE);
        display.setCursor(0,0);
        display.print("Temp: ");
        display.print(currentTemp);
        display.println(" C");
        display.setCursor(0,20);
        display.print("Humidity: ");
        display.print(currentHum);
        display.println(" %");
        display.display();

        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}