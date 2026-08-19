"""Constants for the G410 Ring Event integration."""

DOMAIN = "g410_doorbell_event"
NAME = "G410 Ring Event"
VERSION = "0.1.0"

CONF_NODE_ID = "node_id"
CONF_ENDPOINT_ID = "endpoint_id"

ENTITY_RING = "ring"
EVENT_DOORBELL = "g410_doorbell_event"

OCCUPANCY_SENSING_CLUSTER_ID = 0x0406
INITIAL_OCCUPIED_SUPPRESSION_SECONDS = 10.0
