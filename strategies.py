from abc import ABC, abstractmethod
from collections.abc import Iterable
from math import floor
from random import uniform
from typing import Self

from pandas import DataFrame as df

from constants import *
from enums import MiningStatus as MS
from formatters import format_duration
from userinput import UserInput


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

    def sort_targets(self) -> list[int]:
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

    @property
    def total_hydro(self) -> float:
        return sum(self._roids)
    
    @property
    def field_state(self) -> list[list[str | float]]:
        return [
            [f"r{i:02}", self._roids[i], self._collected[i]]
            for i in range(MAX_ROIDS)
        ]
    
    def drained_roid(self) -> bool:
        return all([
            self._gen_counter == MAX_ROIDS - START_ROIDS,
            min(self._roids) == 0
        ])


class MiningStrategy(ABC):
    def __init__(self, inputs: UserInput) -> None:
        self._inputs = inputs
        self._base_hf = HydroField(DRS_STARTING_HYDRO[self._inputs.drslv])
        self._base_time = 0
        self._base_mining_progress_data = []
        self._base_hydro_field_data = []
        self._mining_delay = 0
        self._max_mining_delay = 2 * self._inputs.genrich_cd
        self._max_time = 40 * MINUTE
        self._status = MS.CLEARING
        self._reset()
    
    def _reset(self) -> None:
        self._hf = self._base_hf.copy()
        self._time = self._base_time
        self._last_genrich = self._base_time
        self._last_artboost = 0
        self._mining_progress_data = self._base_mining_progress_data[:]
        self._hydro_field_data = self._base_hydro_field_data[:]
        self._status = MS.GENRICH
        # All miners combined
        self._tank = 0
        self._tank_max = self._inputs.tanksize * self._inputs.minerqty
        self._boosts = 0
    
    @abstractmethod
    def run(self) -> bool:
        pass

    def tick(self) -> None:
        self._time += self._inputs.tick_len

    def genrich_and_write_data(self) -> None:
        self._hf.genrich(self._inputs.gen, self._inputs.enr)
        self.write_mining_progress_data()

    def write_all_data(self) -> None:
        self.write_mining_progress_data()
        self.write_hydro_field_data()
    
    def write_mining_progress_data(self) -> None:
        self._mining_progress_data.append([
            self._time,
            format_duration(self._time),
            self._boosts,
            self._tank,
            self._hf.total_hydro,
            self._status,
        ])
    
    def write_hydro_field_data(self) -> None:
        self._hydro_field_data.extend([
            [self._time, format_duration(self._time), *record]
            for record in self._hf.field_state
        ])

    def read_mining_progress_data(self) -> df:
        return df.from_records(
            self._mining_progress_data,
            columns=[
                "Time", "Duration", "Boosts", "Tank", "Total Hydro",
                "Mining Status",
            ]
        )
    
    def read_hydro_field_data(self) -> df:
        return df.from_records(
            self._hydro_field_data,
            columns=["Time", "Duration", "Roid", "Remaining", "Collected"]
        ).melt(
            ["Time", "Duration", "Roid"],
            var_name="Status",
            value_name="Hydro"
        )

    def get_mining_delay(self) -> int:
        return self._mining_delay + self._inputs.tick_len
    
    def get_remote_targets(self) -> list[int]:
        return self._hf.sort_targets()[:self._inputs.remote_max_targets]
    
    ### Mining components
    def exit_miners(self) -> None:
        completed_mining = self._time
        self._status = MS.EXITING
        while self._time < completed_mining + self._inputs.exit_dur:
            self.tick()
            self.write_all_data()


class ContinuousMining(MiningStrategy):
    def _base_field_setup(self) -> None:
        # Write starting values
        self.write_all_data()
        while self._time < self._inputs.genrich_start:
            self.tick()
            self.write_all_data()
        # First genrich
        self.genrich_and_write_data()
        self._status = MS.GENRICH
        # Write intermediate values
        while self._time < self._inputs.genrich_start + self._inputs.genrich_cd:
            self.tick()
            self.write_all_data()
        # Second genrich
        self.genrich_and_write_data()
        # Set as base values
        self._base_hf = self._hf.copy()
        self._base_time = self._time  # The same tick as 2nd genrich
        self._base_mining_progress_data = self._mining_progress_data[:]
        self._base_hydro_field_data = self._hydro_field_data[:]
    
    def run(self) -> bool:
        self._base_field_setup()
        while self._mining_delay < self._max_mining_delay:
            self._reset()
            targets = self.get_remote_targets()
            delay_reference = self._last_genrich
            while self._time < self._max_time:
                self.tick()
                # TODO: Abstract away these components into MiningStrategy
                #       superclass?
                # Mine
                if self._time >= delay_reference + self._mining_delay:
                    if self._time > self._last_artboost + self._inputs.rm_lag:
                        # Strictly greater since one tick passed after last
                        #   artboost already
                        self._status = MS.MINING
                        total_mined = min(
                            self._inputs.total_mining_speed,
                            self._tank_max - self._tank
                        )
                        self._tank += total_mined
                        self._hf.collect(total_mined, targets)
                    else:
                        self._status = MS.WAITING
                self.write_all_data()
                # Boost and Move
                if self._tank >= self._inputs.ab * self._inputs.minerqty:
                    self._tank -= self._inputs.ab * self._inputs.minerqty
                    self._boosts += self._inputs.minerqty
                    self._last_artboost = self._time
                    targets = self.get_remote_targets()
                    self.write_mining_progress_data()
                # Enrich
                if self._time >= self._last_genrich + self._inputs.genrich_cd:
                    self.genrich_and_write_data()
                    self._last_genrich = self._time
                # Checks
                if self._hf.drained_roid():
                    # Retry
                    break
                if self._boosts >= self._inputs.boostqty:
                    self.exit_miners()
                    return True
            else:
                # Exceeded max simulation time
                return False
            # Increase delay
            self._mining_delay += self._inputs.tick_len
        
        # Exceeded max mining delay
        return False
