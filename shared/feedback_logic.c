#include "feedback_logic.h"

void feedback_logic_init(feedback_logic_t *logic)
{
    if (logic == NULL) return;
    logic->previous_rep_count = 0;
    logic->initialized = false;
}

feedback_event_t feedback_logic_update(feedback_logic_t *logic,
                                       const motion_packet_t *packet)
{
    if (logic == NULL || packet == NULL) return FEEDBACK_EVENT_NONE;

    if (!logic->initialized) {
        logic->previous_rep_count = packet->rep_count;
        logic->initialized = true;
        return FEEDBACK_EVENT_NONE;
    }

    if (packet->rep_count <= logic->previous_rep_count) {
        return FEEDBACK_EVENT_NONE;
    }

    logic->previous_rep_count = packet->rep_count;
    return packet->quality == MOTION_QUALITY_OK
        ? FEEDBACK_EVENT_SUCCESS
        : FEEDBACK_EVENT_NONE;
}
