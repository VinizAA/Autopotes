#ifndef SENSOR_DATA_H
#define SENSOR_DATA_H

#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>

struct SensorData {
    float temperature;
    float humidity;
    SemaphoreHandle_t mutex;
};

extern SensorData sensorData;

#endif // SENSOR_DATA_H