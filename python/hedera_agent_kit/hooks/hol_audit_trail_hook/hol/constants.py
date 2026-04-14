HCS1_CHUNK_THRESHOLD = 1024
HCS1_CHUNK_ENVELOPE_SIZE = 16  # JSON envelope overhead: {"o":NNN,"c":"..."} ≈ 16 bytes
HCS1_CHUNK_SIZE = HCS1_CHUNK_THRESHOLD - HCS1_CHUNK_ENVELOPE_SIZE

HCS2_PROTOCOL = "hcs-2"

HCS2_OPERATION = {
    "REGISTER": "register",
    "UPDATE": "update",
    "DELETE": "delete",
    "MIGRATE": "migrate",
}
