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

static void expect_event(feedback_logic_t *logic, motion_state_t state,
                         motion_quality_t quality, uint16_t reps,
                         feedback_event_t expected)
{
    motion_packet_t sample = packet(state, quality, reps);
    assert(feedback_logic_update(logic, &sample) == expected);
}

int main(void)
{
    feedback_logic_t logic;
    feedback_logic_init(&logic);

    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_NONE, 0,
                 FEEDBACK_EVENT_NONE);
    expect_event(&logic, MOTION_STATE_ELBOW_FLEXION, MOTION_QUALITY_NONE, 0,
                 FEEDBACK_EVENT_NONE);
    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_TOO_FAST, 0,
                 FEEDBACK_EVENT_NONE);
    expect_event(&logic, MOTION_STATE_IDLE,
                 MOTION_QUALITY_INSUFFICIENT_RANGE, 0, FEEDBACK_EVENT_NONE);

    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 1,
                 FEEDBACK_EVENT_SUCCESS);
    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 1,
                 FEEDBACK_EVENT_NONE);

    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 3,
                 FEEDBACK_EVENT_SUCCESS);
    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 2,
                 FEEDBACK_EVENT_NONE);
    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 3,
                 FEEDBACK_EVENT_NONE);
    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 4,
                 FEEDBACK_EVENT_SUCCESS);

    feedback_logic_init(&logic);
    expect_event(&logic, MOTION_STATE_IDLE, MOTION_QUALITY_OK, 0,
                 FEEDBACK_EVENT_NONE);

    puts("test_feedback_logic: PASS");
    return 0;
}
