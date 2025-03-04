#ifndef DHT_TASK_H
#define DHT_TASK_H

#include <Arduino.h>
#include "DHT.h"
#include "sensor_data.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#define DHTPIN 4
#define DHTTYPE DHT11

extern DHT dht;
extern TaskHandle_t DhtTaskHandle;

void initDhtTask();
void DhtTask(void *pvParameters);

#endif 