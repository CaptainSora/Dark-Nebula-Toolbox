from dataclasses import dataclass

from constants import *


@dataclass(kw_only=True, frozen=True)
class UserInput:
    drslv: int
    genlv: int
    enrlv: int
    ablv: int
    mboostlv: int
    remotelv: int
    minerlv: int
    minerqty: int
    boostqty: int
    _genrich_start_min: int
    _genrich_lag: int = 0
    tick_len: int = 10
    rmbug_lag: int = 0

    @property
    def gen(self) -> int:
        return GENESIS[self.genlv]
    
    @property
    def enr(self) -> float:
        return ENRICH[self.enrlv]
    
    @property
    def ab(self) -> int:
        return ARTIFACT_BOOST[self.ablv]
    
    @property
    def tanksize(self) -> int:
        return MINER_TANK[self.minerlv]
    
    @property
    def total_mining_speed(self) -> float:
        # Total mining speed in hydro/tick
        return (
            MINER_SPEED[self.minerlv]
            * MINING_BOOST[self.mboostlv]
            * REMOTE_MINING[self.remotelv] / REMOTE_MINING_REDUCTION
            * self.minerqty
            / MINUTE * self.tick_len
        )
    
    @property
    def remote_max_targets(self) -> int:
        return REMOTE_MINING[self.remotelv]
    
    @property
    def genrich_start(self) -> int:
        return self._genrich_start_min * MINUTE
    
    @property
    def genrich_cd(self) -> int:
        return 5 * MINUTE + self._genrich_lag
