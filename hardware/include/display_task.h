#ifndef DISPLAY_TASK_H
#define DISPLAY_TASK_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "sensor_data.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C

extern Adafruit_SSD1306 display;
extern TaskHandle_t displayTaskHandle;

void initDisplayTask();
void displayTask(void *pvParameters);

#endif // DISPLAY_TASK_H