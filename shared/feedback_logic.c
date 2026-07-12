#include "feedback_logic.h"

void feedback_logic_init(feedback_logic_t *logic)
{
    if (logic == NULL) return;
    logic->previous_state = MOTION_STATE_IDLE;
    logic->initialized = false;
}

feedback_event_t feedback_logic_update(feedback_logic_t *logic,
                                       const motion_packet_t *packet)
{
    if (logic == NULL || packet == NULL) return FEEDBACK_EVENT_NONE;

    const motion_state_t state = (motion_state_t)packet->state;
    if (!logic->initialized) {
        logic->previous_state = state;
        logic->initialized = true;
        return FEEDBACK_EVENT_NONE;
    }

    const bool completed = logic->previous_state != MOTION_STATE_IDLE &&
                           state == MOTION_STATE_IDLE;
    logic->previous_state = state;
    if (!completed) return FEEDBACK_EVENT_NONE;

    const motion_quality_t quality = (motion_quality_t)packet->quality;
    if (quality == MOTION_QUALITY_TOO_FAST ||
        quality == MOTION_QUALITY_INSUFFICIENT_RANGE) {
        return FEEDBACK_EVENT_WARNING;
    }
    return quality == MOTION_QUALITY_OK ? FEEDBACK_EVENT_SUCCESS
                                       : FEEDBACK_EVENT_NONE;
}
