from collections import namedtuple
from datetime import datetime as dt
from time import sleep

import altair as alt
from numpy import pi
import pandas as pd
import streamlit as st

from checks import remote_mining_bug_active
from enums import MiningStatus as MS
from formatters import format_duration
from simulation import *
from strategies import ContinuousMining


VERSION = "0.5.0 (Beta)"


### Page Setup
st.set_page_config(
    page_title="DRS Mining Simulator",
    menu_items={
        "Get help": None,
        "Report a Bug": None,
        "About": None
    }
)
st.title("DRS Mining Simulator")
st.caption(
    f"Version {VERSION} - Last deployed {dt.today().strftime('%b %d, %Y')}"
)


### Input Setup
def default(label, initvalue):
    if label not in st.session_state:
        st.session_state[label] = initvalue

Module = namedtuple("Module", ["name", "path", "min", "max", "init"])

miner_img_paths = [f"Img/MS{x}.webp" for x in range(0, 8)]

module_inputs = [
    Module("Mining Boost", "MiningBoost", 0, 15, 12),
    Module("Remote Mining", "RemoteMining", 1, 15, 9),
    Module("Crunch", "Crunch", 0, 15, 0),
    Module("Genesis", "Genesis", 0, 15, 13),
    Module("Enrich", "Enrich", 0, 15, 12),
    Module("Artifact Boost", "ArtifactBoost", 1, 15, 13),
    Module("DRS Level", "RedStar", 7, 12, 10),
    Module("Miner Level", "Miner Level", 1, 7, 6),
    Module("Miner Quantity", "MS6", 1, 4, 2),
    Module("Target Number of Artifact Boosts", "ArtifactBoost", 1, 25, 18),
    Module("First Genrich (Minutes)", "Genesis", 0, 9, 2),
]

def change_mod_levels():
    pass

module_values = [None for _ in module_inputs]

modnum = 0


def set_input_img_field(img: st.container,
                        field: st.container,
                        mod: Module) -> None:
    # Field must be defined before image for dynamic image switching
    with field:
        module_values[modnum] = st.number_input(
            mod.name, min_value=mod.min, max_value=mod.max, step=1,
            format="%d", value=mod.init, key=mod.name,
            on_change=change_mod_levels,
        )
    with img:
        if mod.name == "Miner Level":
            st.image(miner_img_paths[st.session_state["Miner Level"]])
        else:
            st.image(f"Img/{mod.path}.webp")


### Inputs
for _ in range(3):
    for col in st.columns(3, gap="medium"):
        with col:
            img, field = st.columns([1, 3], vertical_alignment="center")
            set_input_img_field(img, field, module_inputs[modnum])
        modnum += 1

left, right = st.columns([3, 2], gap="small")
with left:
    img, field = st.columns([2, 13], vertical_alignment="center")
    set_input_img_field(img, field, module_inputs[-2])

with right:
    img, field = st.columns([1, 4], vertical_alignment="center")
    set_input_img_field(img, field, module_inputs[-1])


### Advanced Inputs
default("Remote Mining Bug Delay", 0)
with st.expander("Advanced Settings"):
    st.session_state["Simulation Tick Length"] = st.select_slider(
        "Simulation Tick Length (seconds)",
        options=[5, 10, 20],
        value=10
    )
    st.session_state["Enrich Cooldown Delay"] = st.select_slider(
        "Extra delay between enrich cycles (seconds)",
        options=[
            i * st.session_state["Simulation Tick Length"]
            for i in range(5)
        ],
        value=st.session_state["Simulation Tick Length"],
    )
    st.session_state["Remote Mining Bug Delay"] = st.select_slider(
        (
            "Extra mining delay after artifact boost due to "
            "Remote Mining bug (seconds)"
        ),
        options=[
            i * st.session_state["Simulation Tick Length"]
            for i in range(5)
        ],
        value=st.session_state["Simulation Tick Length"],
        disabled=not remote_mining_bug_active(
            st.session_state["Miner Level"],
            st.session_state["Artifact Boost"]
        ),
    )
    st.session_state["Exit Duration"] = st.select_slider(
        "Time required to fly miners out of DRS (seconds)",
        options=list(range(
            60, 121, st.session_state["Simulation Tick Length"]
        )),
        value=80
    )


### Simulation Setup
default("DRS Time", 0)
default("Simulation", None)
default("Inputs", None)

def get_simulation() -> None:
    if any([st.session_state[mod.name] is None for mod in module_inputs]):
        return
    st.session_state["Inputs"] = UserInput(
        drslv=st.session_state["DRS Level"],
        genlv=st.session_state["Genesis"],
        enrlv=st.session_state["Enrich"],
        ablv=st.session_state["Artifact Boost"],
        mboostlv=st.session_state["Mining Boost"],
        remotelv=st.session_state["Remote Mining"],
        minerlv=st.session_state["Miner Level"],
        minerqty=st.session_state["Miner Quantity"],
        boostqty=st.session_state["Target Number of Artifact Boosts"],
        _genrich_start_min=st.session_state["First Genrich (Minutes)"],
        _genrich_lag=st.session_state["Enrich Cooldown Delay"],
        tick_len=st.session_state["Simulation Tick Length"],
        _rmbug_lag=st.session_state["Remote Mining Bug Delay"],
        exit_dur=st.session_state["Exit Duration"],
    )
    st.session_state["Simulation"] = (
        Simulation(st.session_state["Inputs"])
        .set_strategy(ContinuousMining)
        .run()
    )

def make_linechart(mining_progress, duration):
    tick_values = [
        dur for dur in mining_progress["Duration"]
        if dur[-3:] == "00s"
    ]
    line = (
        alt.Chart(mining_progress[["Duration", "Total Hydro"]])
        .mark_line()
        .encode(
            alt.X("Duration:O")
                .axis(
                    title="DRS Time (seconds)",
                    grid=True,
                    values=tick_values,
                ),
            alt.Y("Total Hydro")
                .scale(domain=(0, 21000), nice=False)
                .axis(title="Total Hydrogen in Sector")
        )
    )

    max_hydro = (
        alt.Chart(pd.DataFrame({"Max Hydro": [21000]}))
        .mark_rule(color="red")
        .encode(alt.Y("Max Hydro"))
    )
    cur_dur = (
        alt.Chart(pd.DataFrame({"x": [duration]}))
        .mark_rule(color="orange")
        .encode(alt.X("x"))
    )

    mp_unique = mining_progress.drop_duplicates("Duration")
    
    rect = (
        alt.Chart(mp_unique)
        .mark_rect()
        .encode(
            x="Duration:O",
            opacity=alt.value(0.2),
            color=alt.Color("Mining Status:N", legend=None),
        )
    )

    return line + rect + line + max_hydro + cur_dur

def make_barchart(hydro_field, duration):
    bar = (
        alt.Chart(hydro_field[hydro_field["Duration"] == duration])
        .mark_bar()
        .encode(
            alt.X("Roid")
                .axis(labels=False, title="Asteroids in Sector"),
            alt.Y("Hydro")
                .scale(domain=(0, 1500), nice=False)
                .axis(
                    title="Hydrogen per Asteroid",
                    values=[0, 300, 600, 900, 1200, 1500],
                ),
            color="Status",
            opacity=alt.condition(
                alt.datum.Active == True,
                alt.value(1), alt.value(0.6)
            )
        )
    )

    rule = (
        alt.Chart(pd.DataFrame({"Max Hydro": [1500]}))
        .mark_rule(color="red")
        .encode(alt.Y("Max Hydro"))
    )

    return bar + rule

def make_donutchart(mining_progress, duration):
    mp_unique = mining_progress.drop_duplicates("Time")
    time = mp_unique.loc[mp_unique.Duration == duration, "Time"].values[0]

    # Don't count the action at time 0
    mp_unique = mp_unique[mp_unique["Time"] > 0]

    # Count total and elapsed actions
    all_actions = (
        mp_unique
        .value_counts("Mining Status")
    ) * st.session_state["Simulation Tick Length"]
    elapsed_actions = (
        mp_unique[mp_unique["Time"] <= int(time)]
        .value_counts("Mining Status")
    ) * st.session_state["Simulation Tick Length"]

    # Create df
    index = pd.DataFrame(index=[ms.value for ms in MS])
    source = (
        pd.concat([index, all_actions, elapsed_actions], axis=1)
        .reset_index()
        .rename(columns={
            "index": "Status",
            0: "Total Duration (seconds)",
            1: "Elapsed Duration (seconds)"
        })
        .fillna(value=0)
    )

    innerRadius = 48
    outerRadius = 144

    source["Added Radius"] = (
        source["Elapsed Duration (seconds)"]
        / source["Total Duration (seconds)"]
        * (outerRadius - innerRadius)
    )

    # Create "base" chart showing total actions
    donut = (
        alt.Chart(source)
        .mark_arc(innerRadius=innerRadius, outerRadius=outerRadius)
        .encode(
            theta=alt.Theta("Total Duration (seconds)", stack=True),
            color="Status:N",
            opacity=alt.value(0.3),
        )
        .properties(
            title="Miner Time Spent Breakdown"
        )
    )

    # Problem: cannot control radii of each slice individually
    # Solution: create n additional donut charts on top of the "base" chart,
    #           each with only its slice visible. Control the radius of each
    #           additional chart as desired
    slices = []
    for ms in MS:
        added_radius = (
            source.loc[source["Status"] == ms.value, "Added Radius"].values[0]
        )
        donut_slice = (
            alt.Chart(source)
            .mark_arc(
                innerRadius=innerRadius,
                outerRadius=innerRadius + added_radius
            )
            .encode(
                theta=alt.Theta("Total Duration (seconds)", stack=True),
                color="Status:N",
                opacity=alt.condition(
                    alt.datum.Status == ms.value,
                    alt.value(1), alt.value(0)
                ),
                tooltip=[
                    "Total Duration (seconds)",
                    "Elapsed Duration (seconds)",
                    "Status",
                ],
            )
        )
        slices.append(donut_slice)

    # Stack charts and configure
    layer = (
        alt.layer(donut, *slices)
        .configure_title(anchor="middle")
        .configure_legend(offset=-50, labelLimit=0, symbolOpacity=1)
    )

    return layer


### Button
left_padding, center, right_padding = st.columns([3, 2, 3])
with center:
    st.write("")
    st.button(
        "Simulate!",
        on_click=get_simulation,
        type="primary",
        use_container_width=True,
    )
    st.write("")

st.warning(
    "Warning: Crunch is currently unsupported by the mining simulation",
    icon="⚠️",
)

sim: Simulation = st.session_state["Simulation"]
inputs: UserInput = st.session_state["Inputs"]


### Output
if sim is not None and inputs is not None and sim.valid:
    mining_progress = sim.read_mining_progress_data()
    hydro_field = sim.read_hydro_field_data()

    with st.expander("Initial conditions"):
        st.markdown(f"""
        DRS{inputs.drslv} with first genrich at
        {format_duration(inputs.genrich_start)} DRS time  
        Genrich {inputs.genlv}/{inputs.enrlv},
        AB {inputs.ablv},
        {inputs.minerqty}x Miner {inputs.minerlv} with 
        {inputs.mboostlv}/{inputs.remotelv} speed  
        Targeting a total of {inputs.boostqty} artifact boosts
        """)

    st.info(
        f"Delay mining until {format_duration(sim.get_mining_delay())}"
        f" after 2nd genrich",
        icon=":material/schedule:"
    )

    total_boost_qty = mining_progress["Boosts"].values[-1]
    last_boost_time = (
        mining_progress
        .loc[mining_progress["Boosts"] == total_boost_qty]
        ["Duration"]
        .values[0]
    )
    drs_exit_time = mining_progress["Duration"].values[-1]

    st.info(
        f"{total_boost_qty} artifact boosts mined at "
        f"{last_boost_time} DRS time",
        icon=":material/shopping_cart_checkout:"
    )

    st.info(
        f"Miners reach jump gate at {drs_exit_time} DRS time",
        icon=":material/logout:"
    )

    time_min = 0
    time_max = mining_progress["Time"].values[-1]

    tab1, tab2 = st.tabs(["Interactive Graphs", "Animated Graphs"])

    with tab1:
        padding, slider_col = st.columns([1, 9])
        with slider_col:
            st.session_state["DRS Time"] = st.select_slider(
                "DRS Time (seconds)",
                options=list(dict.fromkeys(mining_progress["Duration"])),
                key="slider"
            )

        st.altair_chart(
            make_linechart(mining_progress, st.session_state["DRS Time"]),
            use_container_width=True,
        )
        st.altair_chart(
            make_barchart(hydro_field, st.session_state["DRS Time"]),
            use_container_width=True,
        )
        st.altair_chart(
            make_donutchart(mining_progress, st.session_state["DRS Time"]),
            use_container_width=True,
        )
    
    with tab2:
        col1, col2, col3 = st.columns([1, 1, 6])
        with col1:
            play_fast = st.button("Play (Fast)")
        with col2:
            play_slow = st.button("Play (Slow)")
        with col3:
            pbar = st.progress(
                0,
                text=f"DRS Time: {format_duration(time_min)}",
            )
        line = st.altair_chart(
            make_linechart(mining_progress, format_duration(time_min)),
            use_container_width=True,
        )
        bar = st.altair_chart(
            make_barchart(hydro_field, format_duration(time_min)),
            use_container_width=True,
        )
        donut = st.altair_chart(
            make_donutchart(mining_progress, format_duration(time_min)),
            use_container_width=True,
        )

        tick = st.session_state["Simulation Tick Length"]
        if play_fast or play_slow:
            for time in range(time_min, time_max + tick, tick):
                pbar.progress(
                    time / time_max,
                    text = f"DRS Time: {format_duration(time)}"
                )
                line.altair_chart(
                    make_linechart(mining_progress, format_duration(time)),
                    use_container_width=True,
                )
                bar.altair_chart(
                    make_barchart(hydro_field, format_duration(time)),
                    use_container_width=True,
                )
                donut.altair_chart(
                    make_donutchart(mining_progress, format_duration(time)),
                    use_container_width=True,
                )
                sleep(0 if play_fast else 0.02 * tick)
elif sim is not None and inputs is not None:
    st.error(
        "Simulation failed to find a solution, please verify your inputs!"
    )
