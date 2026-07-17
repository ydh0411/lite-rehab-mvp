#ifndef LITE_REHAB_FEEDBACK_LOGIC_H
#define LITE_REHAB_FEEDBACK_LOGIC_H

#include <stdbool.h>

#include "motion_packet.h"

typedef enum {
    FEEDBACK_EVENT_NONE = 0,
    FEEDBACK_EVENT_SUCCESS = 1,
    FEEDBACK_EVENT_WARNING = 2,
} feedback_event_t;

typedef struct {
    uint16_t previous_rep_count;
    bool initialized;
} feedback_logic_t;

void feedback_logic_init(feedback_logic_t *logic);
feedback_event_t feedback_logic_update(feedback_logic_t *logic,
                                       const motion_packet_t *packet);

#endif
