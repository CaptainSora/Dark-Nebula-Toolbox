from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from math import floor
from random import uniform
from typing import Self

from pandas import DataFrame as df

from game_constants import *


class HydroField:
    def __init__(self, total_hydro: int) -> None:
        self._roids = [0 for _ in range(MAX_ROIDS)]
        self._collected = [0 for _ in range(MAX_ROIDS)]
        self._roids[0:START_ROIDS-1] = [
            round(uniform(total_hydro / 8 * 0.9, total_hydro / 8 * 1.1))
            for _ in range(START_ROIDS-1)
        ]
        self._roids[START_ROIDS-1] = total_hydro - sum(self._roids)
        self._gen_counter = 0
    
    def copy(self) -> Self:
        new_hf = HydroField(0)
        new_hf._roids = self._roids[:]
        new_hf._collected = self._collected[:]
        new_hf._gen_counter = self._gen_counter
        return new_hf
    
    def genrich(self, gen_amt: int, enr_mult: float) -> None:
        # Genesis
        new_roid_amt = gen_amt // GENESIS_ROIDS
        cur_roids = START_ROIDS + self._gen_counter
        if cur_roids < MAX_ROIDS:
            new_roids = min(GENESIS_ROIDS, MAX_ROIDS - cur_roids)
            self._roids[cur_roids:cur_roids+new_roids] = (
                [new_roid_amt for _ in range(new_roids)]
            )
            self._gen_counter += new_roids
        # Enrich
        self._roids = [min(floor(r * enr_mult), H_MAX) for r in self._roids]
        self._collected = [0 for _ in range(MAX_ROIDS)]

    def get_targets(self) -> list[int]:
        return [
            idx for idx, value in sorted(
                enumerate(self._roids), key=lambda x: x[1], reverse=True
            )
        ]

    def collect(self, total_amt: float, targets: Iterable[int]) -> None:
        amt_per_roid = total_amt / len(targets)
        for idx in targets:
            self._collected[idx] += min(self._roids[idx], amt_per_roid)
            self._roids[idx] -= min(self._roids[idx], amt_per_roid)

    def get_total_hydro(self) -> float:
        return sum(self._roids)
    
    def get_field_state(self) -> list[list[str | float]]:
        return [
            [f"r{i:02}", self._roids[i], self._collected[i]]
            for i in range(MAX_ROIDS)
        ]
    
    def drained_roid(self) -> bool:
        return all([
            self._gen_counter == MAX_ROIDS - START_ROIDS,
            min(self._roids) == 0
        ])


@dataclass(kw_only=True, frozen=True)
class PlayerInputs:
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


class Strategy(ABC):
    def __init__(self, inputs: PlayerInputs) -> None:
        self._inputs = inputs
        self._base_hf = HydroField(DRS_STARTING_HYDRO[self._inputs.drslv])
        self._base_time = 0
        self._base_mining_progress_log = []
        self._base_hydro_field_log = []
        self._mining_delay = 0
        self._max_mining_delay = 2 * self._inputs.genrich_cd
        self._max_time = 40 * MINUTE
        self._reset()
    
    def _reset(self) -> None:
        self._hf = self._base_hf.copy()
        self._time = self._base_time
        self._last_genrich = self._base_time
        self._mining_progress_log = self._base_mining_progress_log[:]
        self._hydro_field_log = self._base_hydro_field_log[:]
        self._tank = 0
        self._boosts = 0
    
    @abstractmethod
    def run(self) -> bool:
        pass

    def tick(self) -> None:
        self._time += self._inputs.tick_len

    def genrich_and_log(self) -> None:
        self._hf.genrich(self._inputs.gen, self._inputs.enr)
        self.log_mining_progress()

    def log(self) -> None:
        self.log_mining_progress()
        self.log_hydro_field()
    
    def log_mining_progress(self) -> None:
        self._mining_progress_log.append([
            self._time,
            self._boosts,
            self._tank,
            self._hf.get_total_hydro()
        ])
    
    def log_hydro_field(self) -> None:
        self._hydro_field_log.extend([
            [self._time, *record]
            for record in self._hf.get_field_state()
        ])

    def get_mining_progress_log(self) -> df:
        return df.from_records(
            self._mining_progress_log,
            columns=["Time", "Boosts", "Tank", "Total Hydro"]
        )
    
    def get_hydro_field_log(self) -> df:
        return df.from_records(
            self._hydro_field_log,
            columns=["Time", "Roid", "Remaining", "Collected"]
        ).melt(
            ["Time", "Roid"],
            var_name="Status",
            value_name="Hydro"
        )

    def get_mining_delay(self) -> int:
        return self._mining_delay + self._inputs.tick_len
    
    def get_remote_targets(self) -> list[int]:
        return self._hf.get_targets()[:self._inputs.remote_max_targets]


class ContinuousMining(Strategy):
    def _base_field_setup(self) -> None:
        # Log starting values
        self.log()
        while self._time < self._inputs.genrich_start:
            self.tick()
            self.log()
        # First genrich
        self.genrich_and_log()
        # Log intermediate values
        while self._time < self._inputs.genrich_start + self._inputs.genrich_cd:
            self.tick()
            self.log()
        # Second genrich
        self.genrich_and_log()
        # Set as base values
        self._base_hf = self._hf.copy()
        self._base_time = self._time  # The same tick as 2nd genrich
        self._base_mining_progress_log = self._mining_progress_log[:]
        self._base_hydro_field_log = self._hydro_field_log[:]
    
    def run(self) -> bool:
        self._base_field_setup()
        while self._mining_delay < self._max_mining_delay:
            self._reset()
            targets = self.get_remote_targets()
            delay_reference = self._last_genrich
            while self._time < self._max_time:
                self.tick()
                # Mine
                if self._time >= delay_reference + self._mining_delay:
                    self._tank += self._inputs.total_mining_speed
                    self._hf.collect(self._inputs.total_mining_speed, targets)
                self.log()
                # Boost and Move
                if self._tank >= self._inputs.ab * self._inputs.minerqty:
                    self._tank -= self._inputs.ab * self._inputs.minerqty
                    self._boosts += self._inputs.minerqty
                    targets = self.get_remote_targets()
                    self.log_mining_progress()
                # Enrich
                if self._time >= self._last_genrich + self._inputs.genrich_cd:
                    self.genrich_and_log()
                    self._last_genrich = self._time
                # Checks
                if self._hf.drained_roid():
                    # Increase delay and retry
                    self._mining_delay += self._inputs.tick_len
                    break
                if self._boosts >= self._inputs.boostqty:
                    return True
            else:
                # Exceeded max simulation time
                return False
            # Increase delay
            self._mining_delay += self._inputs.tick_len
        
        # Exceeded max mining delay
        return False


class Simulation:
    def __init__(self, inputs: PlayerInputs) -> None:
        self._valid = False
        self._strategy = None
        self._inputs = inputs

    @property
    def valid(self) -> None:
        return self._valid
    
    @property
    def strategy(self) -> Strategy:
        return self._strategy
    
    def set_strategy(self, strat: Strategy) -> Self:
        if strat == "Continuous Mining":
            self._strategy = ContinuousMining(self._inputs)
        return self
    
    def run(self) -> Self:
        try:
            self._valid = self._strategy.run()
        except AttributeError:
            self._valid = False
        return self


def to_dur(time):
    return f"{time//MINUTE:02}m{time%MINUTE:02}s"
