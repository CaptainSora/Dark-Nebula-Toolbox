from collections.abc import Iterable
from dataclasses import dataclass
from math import floor
from random import uniform

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
    
    def genrich(self, gen_amt: int, enr_mult: float) -> None:
        # Genesis
        new_roid = gen_amt // GENESIS_ROIDS
        if self._gen_counter == 0:
            self._roids[START_ROIDS:START_ROIDS+GENESIS_ROIDS] = (
                [new_roid for _ in range(GENESIS_ROIDS)]
            )
        elif self._gen_counter == 1:
            self._roids[START_ROIDS+GENESIS_ROIDS:MAX_ROIDS] = (
                [new_roid for _ in range(
                    MAX_ROIDS - (START_ROIDS+GENESIS_ROIDS)
                )]
            )
        self._gen_counter += 1
        # Enrich
        self._roids = [min(floor(r * enr_mult), H_MAX) for r in self._roids]
        self._drained = [0 for _ in range(MAX_ROIDS)]

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
    genrich_start_min: int
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
    def mspeed(self) -> float:
        return (
            MINER_SPEED[self.minerlv]
            * MINING_BOOST[self.mboostlv]
            * REMOTE_MINING[self.remotelv] / REMOTE_MINING_REDUCTION
            * self.minerqty
        )


class Strategy:
    def __init__(self, inputs: PlayerInputs, hydrofield: HydroField) -> None:
        self._inputs = inputs
        self._hydrofield = hydrofield
        self._mining_progress_log = []
        self._hydro_field_log = []
    
    def run(self) -> None:
        # To be overridden by concrete subclasses
        pass

    def log(self) -> None:
        pass

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


class Simulation:
    def __init__(self, inputs: PlayerInputs) -> None:
        self._valid = False
        self._inputs = inputs

    @property
    def valid(self) -> None:
        return self._valid
    
    @staticmethod
    def to_dur(time: int) -> str:
        return f"{time//60:02}m{time%60:02}s"
    
    def set_strategy(strat: Strategy) -> None:
        pass
    
    def run(self) -> None:
        pass


def to_dur(incr):
    return f"{incr//60:02}m{incr%60:02}s"


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
