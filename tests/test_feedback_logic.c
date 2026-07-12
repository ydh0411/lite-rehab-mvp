#include <assert.h>
#include <stdio.h>

#include "feedback_logic.h"

static motion_packet_t packet(motion_state_t state, motion_quality_t quality,
                              uint16_t reps)
{
    return (motion_packet_t){
        .magic = MOTION_PACKET_MAGIC,
        .version = MOTION_PACKET_VERSION,
        .state = (uint8_t)state,
        .quality = (uint8_t)quality,
        .rep_count = reps,
    };
}

int main(void)
{
    feedback_logic_t logic;
    feedback_logic_init(&logic);

    motion_packet_t idle = packet(MOTION_STATE_IDLE, MOTION_QUALITY_NONE, 0);
    motion_packet_t active = packet(MOTION_STATE_ELBOW_FLEXION,
                                    MOTION_QUALITY_NONE, 0);
    motion_packet_t completed_ok = packet(MOTION_STATE_IDLE,
                                          MOTION_QUALITY_OK, 1);
    motion_packet_t completed_short = packet(
        MOTION_STATE_IDLE, MOTION_QUALITY_INSUFFICIENT_RANGE, 1);

    assert(feedback_logic_update(&logic, &idle) == FEEDBACK_EVENT_NONE);
    assert(feedback_logic_update(&logic, &active) == FEEDBACK_EVENT_NONE);
    assert(feedback_logic_update(&logic, &completed_ok) == FEEDBACK_EVENT_SUCCESS);
    assert(feedback_logic_update(&logic, &completed_ok) == FEEDBACK_EVENT_NONE);
    assert(feedback_logic_update(&logic, &active) == FEEDBACK_EVENT_NONE);
    assert(feedback_logic_update(&logic, &completed_short) == FEEDBACK_EVENT_WARNING);
    assert(feedback_logic_update(&logic, &completed_short) == FEEDBACK_EVENT_NONE);

    puts("test_feedback_logic: PASS");
    return 0;
}
