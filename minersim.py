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


def simulate(drslv, genlv, enrlv, ablv, mboostlv, remotelv, minerlv, minerqty, boostqty, tick_len=10):
    """
    Runs a simulation of the hydrogen (h or hydro) asteroids (roids) in the hydro sector of a Hades' Star
    Dark Red Star (DRS).

    drslv: int between 7 and 12 inclusive
    genlv, enrlv, ablv, mboostlv, remotelv: int between 1 and 15 inclusive
    minerlv: int between 1 and 7 inclusive
    minerqty: int at least 1
    boostqty: int at least 1
    tick_len: int as a positive factor of 60

    Returns the output of the simulation, a DataFrame containing the summary of each simulated step,
    and a DataFrame of the detailed asteroid values at each simulated step.
    """
    # Randomly generate hydro roid values
    # Assuming uniformly generated values within 10% of the average hydro value in sector
    base_roids = [round(uniform(DRSHYDRO[drslv] / 8 * 0.9, DRSHYDRO[drslv] / 8 * 1.1)) for _ in range(7)]
    base_roids.append(DRSHYDRO[drslv] - sum(base_roids))
    # Total mining speed in h/min
    mspeed = MINER[minerlv] * MBOOST[mboostlv] * REMOTE[remotelv] / 4 * minerqty
    # Total hydro drained per roid per tick
    drain = mspeed / REMOTE[remotelv] / 60 * tick_len

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
    
    def incr_to_dur(incr):
        return f"{incr//60:02}m{incr%60:02}s"

    delay = 0
    # Prepare simulation to see if delay is sufficient
    while delay <= 5 * 60:
        output = [
            f"Genrich {genlv}/{enrlv}, AB {ablv}",
            f"{minerqty}x Miner {minerlv} at {mboostlv}/{remotelv} targeting {boostqty} boosts",
            f"DRS{drslv} starting with random roid sizes {base_roids} totalling {sum(base_roids)}h",
            f"Mining delayed until {incr_to_dur(delay)} after 2nd genrich"
        ]
        sim_log = []
        field = []

        roids = base_roids[:]

        # 1st genrich
        roids.extend([GEN[genlv] // 4] * 4)
        roids = enrich(roids)
        output.append(f"1st Genrich leaves {sum(roids)} total hydro")

        # 2nd genrich
        roids.extend([GEN[genlv] // 4] * 2)
        roids = enrich(roids)
        output.append(f"2nd Genrich leaves {sum(roids)} total hydro")

        pulled = [0 for _ in roids]

        # Simulate
        incr = 0
        tank = 0
        boosts = 0
        targets = rmtargets(roids)

        # Capping simulation at 25 minutes past 2nd genrich
        while incr < 25 * 60:
            # Mine
            if incr >= delay:
                tank += drain * REMOTE[remotelv]
                roids, pulled = tick(roids, pulled, targets)
            incr += tick_len
            sim_log.append([incr, boosts, tank/minerqty, sum(roids)])
            for i in range(14):
                field.append([incr, f"r{i:02}", roids[i], pulled[i]])
            # Boost and move
            if tank >= AB[ablv] * minerqty:
                tank -= AB[ablv] * minerqty
                boosts += minerqty
                targets = rmtargets(roids)
            # Enrich
            if incr % 300 == 0:
                roids = enrich(roids)
                output.append(f"Enriched to {sum(roids)} total hydro")
                pulled = [0 for _ in roids]
                sim_log.append([incr, boosts, tank/minerqty, sum(roids)])
            # Checks
            if min(roids) <= 0:
                break
            if boosts >= boostqty:
                output.append(f"Target of {boosts} boosts reached at {incr_to_dur(incr)} after 2nd genrich")
                break
        
        # Check if longer delay needed
        if boosts < boostqty:
            delay += tick_len
            continue
        
        # Create dfs
        sim_log_cols = ["Time", "Boosts", "Tank", "Total Hydro"]
        sim_log = df.from_records(sim_log, columns=sim_log_cols)
        sim_log["Max Hydro"] = 21000
        field_cols = ["Time", "Roid", "Remaining", "Previous Enrich"]
        field = df.from_records(field, columns=field_cols)

        return output, sim_log, field
    
    # Failed simulation
    output = [
        f"Genrich {genlv}/{enrlv}, AB {ablv}",
        f"{minerqty}x Miner {minerlv} at {mboostlv}/{remotelv} targeting {boostqty} boosts",
        f"DRS{drslv} starting with random roid sizes {roids} totalling {sum(roids)}h",
        f"Simulation failed with given parameters!"
    ]
    return output, df(), df()
