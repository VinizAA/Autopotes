#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include "sensor_data.h"
#include "dht_task.h"
#include "display_task.h"

void setup() {
    //Semaphore
    sensorData.mutex = xSemaphoreCreateMutex();

    //Tasks
    initDhtTask();
    initDisplayTask();

    //Scheduler
    vTaskStartScheduler();
}

void loop() {}