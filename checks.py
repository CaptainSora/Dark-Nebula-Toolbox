from constants import *


def remote_mining_bug_active(minerlv: int, ablv: int) -> bool:
    return MINER_TANK[minerlv] == ARTIFACT_BOOST[ablv]
