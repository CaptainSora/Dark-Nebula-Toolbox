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
    
    def get_field_state(self) -> df:
        return df.from_records(
            [
                [f"r{i:02}", self._roids[i], self._collected[i]]
                for i in range(MAX_ROIDS)
            ], columns=["Roid", "Remaining", "Collected"]
        )
    
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
            var_name="Type",
            value_name="Hydro"
        )

    def get_mining_delay(self) -> int:
        return self._mining_delay
    
    def get_remote_targets(self) -> list[int]:
        return self._hf.get_targets()[:self._inputs.remote_max_targets]


class ContinuousMining(Strategy):
    def _base_field_setup(self) -> None:
        # Log starting values
        self.log()
        while self._time < self._inputs.genrich_start:
            self._time += self._inputs.tick_len
            self.log()
        # First genrich
        self._hf.genrich()
        self.log()
        # Log intermediate values
        while self._time < self._inputs.genrich_start + self._inputs.genrich_cd:
            self._time += self._inputs.tick_len
            self.log()
        # Second genrich
        self._hf.genrich()
        self.log()
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
                # Enrich
                if self._time >= self._last_genrich + self._inputs.genrich_cd:
                    self._hf.genrich()
                    self._last_genrich = self._time
                    self.log_mining_progress()
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
    
    @staticmethod
    def to_dur(time: int) -> str:
        return f"{time//MINUTE:02}m{time%MINUTE:02}s"
    
    def set_strategy(self, strat: Strategy) -> None:
        if strat == "Continuous Mining":
            self._strategy = ContinuousMining(self._inputs)
    
    def run(self) -> None:
        try:
            self._valid = self._strategy.run()
        except AttributeError:
            self._valid = False
            return


def to_dur(incr):
    return f"{incr//MINUTE:02}m{incr%MINUTE:02}s"


def simulate(drslv, genlv, enrlv, ablv, mboostlv, remotelv, minerlv, minerqty, 
             boostqty, genrich_start_min, tick_len=10):
    """
    Runs a simulation of the hydrogen (h or hydro) asteroids (roids) in the hydro sector of a Hades' Star
    Dark Red Star (DRS).

    drslv: int between 7 and 12 inclusive
    genlv, enrlv, ablv, mboostlv, remotelv: int between 1 and 15 inclusive
    minerlv: int between 1 and 7 inclusive
    minerqty: int at least 1
    boostqty: int at least 1
    genrich_start_min: int between 0 and 9 inclusive
    tick_len: int as a positive factor of 60

    Returns:
        list[str]: the output of the simulation
        pd.DataFrame: the summary of each simulated step
        pd.DataFrame: the detailed asteroid values at each simulated step (wide format)
        pd.DataFrame: the detailed asteroid values at each simulated step (long format)
        int: the re-enrich target level
    """
    # Randomly generate hydro roid values
    # Assuming uniformly generated values within 10% of the average hydro value in sector
    base_roids = [round(uniform(DRS_STARTING_HYDRO[drslv] / 8 * 0.9, DRS_STARTING_HYDRO[drslv] / 8 * 1.1)) for _ in range(7)]
    base_roids.append(DRS_STARTING_HYDRO[drslv] - sum(base_roids))
    base_roids.extend([0 for _ in range(6)])
    # Total mining speed in h/min
    mspeed = MINER_SPEED[minerlv] * MINING_BOOST[mboostlv] * REMOTE_MINING[remotelv] / 4 * minerqty
    # Total hydro drained per roid per tick
    drain = mspeed / REMOTE_MINING[remotelv] / 60 * tick_len

    # Re-enrich target level
    enr_base = int(H_MAX / ENRICH[enrlv])

    def enrich(roidlist):
        return [min(floor(r * ENRICH[enrlv]), H_MAX) for r in roidlist]

    def rmtargets(roidlist):
        targets = sorted(enumerate(roidlist), key=lambda x: x[1], reverse=True)
        return [t[0] for t in targets][:REMOTE_MINING[remotelv]]
    
    def tick(roidlist, pulledlist, rmtargets):
        return [
            roidlist[i] - drain if i in rmtargets else roidlist[i]
            for i in range(len(roidlist))
        ], [
            pulledlist[i] + drain if i in rmtargets else pulledlist[i]
            for i in range(len(pulledlist))
        ]
    
    # Genrich timers
    genrich_delay = 60 * genrich_start_min
    genrich_cd = 5 * 60

    mining_delay = 0
    # Prepare simulation to see if delay is sufficient
    while mining_delay <= 10 * 60 + tick_len:
        output = [
            f"Genrich {genlv}/{enrlv}, AB {ablv}",
            f"{minerqty}x Miner {minerlv} at {mboostlv}/{remotelv} targeting {boostqty} artifact boosts",
            f"DRS{drslv} starting with random roid sizes {base_roids} totalling {sum(base_roids)}h",
            f"First genrich at {to_dur(genrich_delay)} after start",
            f"Mining delayed until {to_dur(mining_delay)} after 2nd genrich",
        ]
        # Logs
        sim_log = []
        field = []

        # Setup
        time = 0
        roids = base_roids[:]
        pulled = [0 for _ in roids]
        tank = 0
        boosts = 0
        
        # Initial setup
        sim_log.append([time, boosts, tank/minerqty, sum(roids)])
        for i in range(14):
            field.append([time, f"r{i:02}", roids[i], 0])

        while time < genrich_delay:
            time += tick_len
            sim_log.append([time, boosts, tank/minerqty, sum(roids)])
            for i in range(14):
                field.append([time, f"r{i:02}", roids[i], 0])

        # 1st genrich
        roids[8:12] = [GENESIS[genlv] // 4 for _ in range(4)]
        roids = enrich(roids)
        output.append(f"1st Genrich leaves {sum(roids)} total hydro")
        sim_log.append([time, boosts, tank/minerqty, sum(roids)])

        while time < genrich_delay + genrich_cd:
            time += tick_len
            sim_log.append([time, boosts, tank/minerqty, sum(roids)])
            for i in range(14):
                field.append([time, f"r{i:02}", roids[i], 0])

        # 2nd genrich
        roids[12:14] = [GENESIS[genlv] // 4 for _ in range(2)]
        roids = enrich(roids)
        output.append(f"2nd Genrich leaves {sum(roids)} total hydro")
        sim_log.append([time, boosts, tank/minerqty, sum(roids)])

        # Find mining targets
        targets = rmtargets(roids)

        # Capping simulation at 40 minutes
        while time < 40 * 60:
            time += tick_len
            # Mine
            if time > genrich_delay + genrich_cd + mining_delay:
                tank += drain * REMOTE_MINING[remotelv]
                roids, pulled = tick(roids, pulled, targets)
            sim_log.append([time, boosts, tank/minerqty, sum(roids)])
            for i in range(14):
                field.append([time, f"r{i:02}", roids[i], pulled[i]])
            # Boost and move
            if tank >= ARTIFACT_BOOST[ablv] * minerqty:
                tank -= ARTIFACT_BOOST[ablv] * minerqty
                boosts += minerqty
                targets = rmtargets(roids)
            # Enrich
            if (time - genrich_delay) % genrich_cd == 0:
                roids = enrich(roids)
                output.append(f"Enriched to {sum(roids)} total hydro")
                pulled = [0 for _ in roids]
                sim_log.append([time, boosts, tank/minerqty, sum(roids)])
            # Checks
            if min(roids) <= 0 or boosts >= boostqty:
                break
        else:
            output.append("Hit simulation time limit!")
        
        # Check if longer delay needed
        if boosts < boostqty:
            mining_delay += tick_len
            continue

        output.append(f"Target of {boosts} boosts reached at {to_dur(time)}")
        
        # Create dfs
        sim_log_cols = ["Time", "Boosts", "Tank", "Total Hydro"]
        sim_log = df.from_records(sim_log, columns=sim_log_cols)
        sim_log["Max Hydro"] = 21000
        field_cols = ["Time", "Roid", "Remaining", "Previous Enrich"]
        field_wide = df.from_records(field, columns=field_cols)
        field_long = field_wide.melt(["Time", "Roid"], var_name="Type", value_name="Hydro")

        return output, sim_log, field_wide, field_long, enr_base
    
    # Failed simulation
    output = [
        f"Genrich {genlv}/{enrlv}, AB {ablv}",
        f"{minerqty}x Miner {minerlv} at {mboostlv}/{remotelv} targeting {boostqty} artifact boosts",
        f"DRS{drslv} starting with random roid sizes {base_roids} totalling {sum(base_roids)}h",
        f"First genrich at {to_dur(genrich_delay)} after start",
        f"Simulation failed with given parameters!",
    ]
    return output, None, None, None, enr_base
