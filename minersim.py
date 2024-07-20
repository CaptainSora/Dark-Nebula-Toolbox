from dataclasses import dataclass
from math import floor
from random import uniform

from pandas import DataFrame as df

GEN = [0, 120, 160, 200, 240, 280, 320, 400, 480, 560, 640, 720, 800, 1000, 1200, 1400]
ENR = [1, 1.08, 1.16, 1.24, 1.32, 1.4, 1.48, 1.64, 1.8, 1.96, 2.28, 2.6, 2.92, 3.24, 3.56, 4.2]
AB = [0, 10, 20, 30, 40, 60, 150,  250, 400, 550, 800, 1000, 1200, 1400, 1700, 2000]
MBOOST = [1, 1.25, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 7, 8, 9, 10]
REMOTE = [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 14, 14]
MINER = [0, 6, 7.5, 12, 24, 60, 80, 92.3]
HMAX = 1500
DRSHYDRO = [0, 0, 0, 0, 0, 0, 0, 400, 500, 600, 700, 800, 900]


@dataclass(kw_only=True)
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

class Strategy:
    def __init__(self):
        self._GEN = [0, 120, 160, 200, 240, 280, 320, 400, 480, 560, 640, 720, 800, 1000, 1200, 1400]
        self._ENR = [1, 1.08, 1.16, 1.24, 1.32, 1.4, 1.48, 1.64, 1.8, 1.96, 2.28, 2.6, 2.92, 3.24, 3.56, 4.2]
        self._AB = [0, 10, 20, 30, 40, 60, 150,  250, 400, 550, 800, 1000, 1200, 1400, 1700, 2000]
        self._MBOOST = [1, 1.25, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 7, 8, 9, 10]
        self._REMOTE = [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 14, 14]
        self._MINER = [0, 6, 7.5, 12, 24, 60, 80, 92.3]
        self._HMAX = 1500
        self._DRSHYDRO = [0, 0, 0, 0, 0, 0, 0, 400, 500, 600, 700, 800, 900]
    
    def run(self):
        pass


class Simulation:
    def __init__(self, inputs: PlayerInputs):
        self._valid = False
        self._inputs = inputs

    @property
    def valid(self):
        return self._valid
    
    @staticmethod
    def to_dur(time):
        return f"{time//60:02}m{time%60:02}s"
    
    def set_strategy(strat):
        pass
    
    def run(self):
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
    base_roids = [round(uniform(DRSHYDRO[drslv] / 8 * 0.9, DRSHYDRO[drslv] / 8 * 1.1)) for _ in range(7)]
    base_roids.append(DRSHYDRO[drslv] - sum(base_roids))
    base_roids.extend([0 for _ in range(6)])
    # Total mining speed in h/min
    mspeed = MINER[minerlv] * MBOOST[mboostlv] * REMOTE[remotelv] / 4 * minerqty
    # Total hydro drained per roid per tick
    drain = mspeed / REMOTE[remotelv] / 60 * tick_len

    # Re-enrich target level
    enr_base = int(HMAX / ENR[enrlv])

    def enrich(roidlist):
        return [min(floor(r * ENR[enrlv]), HMAX) for r in roidlist]

    def rmtargets(roidlist):
        targets = sorted(enumerate(roidlist), key=lambda x: x[1], reverse=True)
        return [t[0] for t in targets][:REMOTE[remotelv]]
    
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
        roids[8:12] = [GEN[genlv] // 4 for _ in range(4)]
        roids = enrich(roids)
        output.append(f"1st Genrich leaves {sum(roids)} total hydro")
        sim_log.append([time, boosts, tank/minerqty, sum(roids)])

        while time < genrich_delay + genrich_cd:
            time += tick_len
            sim_log.append([time, boosts, tank/minerqty, sum(roids)])
            for i in range(14):
                field.append([time, f"r{i:02}", roids[i], 0])

        # 2nd genrich
        roids[12:14] = [GEN[genlv] // 4 for _ in range(2)]
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
                tank += drain * REMOTE[remotelv]
                roids, pulled = tick(roids, pulled, targets)
            sim_log.append([time, boosts, tank/minerqty, sum(roids)])
            for i in range(14):
                field.append([time, f"r{i:02}", roids[i], pulled[i]])
            # Boost and move
            if tank >= AB[ablv] * minerqty:
                tank -= AB[ablv] * minerqty
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
