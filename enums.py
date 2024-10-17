from enum import StrEnum


class MiningStatus(StrEnum):
    CLEARING = "Clearing cerbs from hydro sector(s)"
    GENRICH = "Waiting for genrich cooldown"
    MINING = "Mining the hydro sector(s)"
    WAITING = "Waiting to restart mining"
    EXITING = "Flying to jump gate"
