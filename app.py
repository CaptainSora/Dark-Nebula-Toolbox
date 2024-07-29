from collections import namedtuple
from datetime import datetime as dt
from time import sleep

import altair as alt
import pandas as pd
import streamlit as st

from formatters import format_duration
from simulation import *
from strategies import ContinuousMining


VERSION = "0.4.0 (Beta)"


st.set_page_config(
    page_title="DRS Mining Simulator",
    menu_items={
        "Get help": None,
        "Report a Bug": None,
        "About": None
    }
)
st.title("DRS Mining Simulator")
st.caption(f"Version {VERSION} - Last deployed {dt.today().strftime('%b %d, %Y')}")


def default(label, initvalue):
    if label not in st.session_state:
        st.session_state[label] = initvalue

Module = namedtuple("Module", ["name", "path", "min", "max", "init"])

miner_img_paths = [f"Img/MS{x}.webp" for x in range(0, 8)]

module_inputs = [
    Module("Mining Boost", "MiningBoost", 0, 15, 11),
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


def set_input_img_field(img: st.container, field: st.container, mod: Module) -> None:
    # Field must be defined before image for dynamic image switching
    with field:
        module_values[modnum] = st.number_input(
            mod.name, min_value=mod.min, max_value=mod.max, step=1, format="%d",
            value=mod.init, key=mod.name, on_change=change_mod_levels)
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
        _genrich_start_min=st.session_state["First Genrich (Minutes)"]
    )
    st.session_state["Simulation"] = (
        Simulation(st.session_state["Inputs"])
        .set_strategy(ContinuousMining)
        .run()
    )

def make_linechart(mining_progress, time):
    line = (
        alt.Chart(mining_progress[["Time", "Total Hydro"]])
        .mark_line()
        .encode(
            alt.X("Time")
                .scale(domain=(0, log["Time"].values[-1]), nice=False)
                .axis(title="DRS Time (seconds)"),
            alt.Y("Total Hydro")
                .scale(domain=(0, 21000), nice=False)
                .axis(title="Total Hydrogen in Sector")
        )
    )

    max_hydro = alt.Chart(pd.DataFrame({"y": [21000]})).mark_rule(color="red").encode(alt.Y("y"))
    cur_time = alt.Chart(pd.DataFrame({"x": [time]})).mark_rule(color="orange").encode(alt.X("x"))

    return line + max_hydro + cur_time

def make_barchart(hydro_field, time):
    bar = (
        alt.Chart(hydro_field[hydro_field["Time"] == time])
        .mark_bar()
        .encode(
            alt.X("Roid")
                .axis(labels=False, title="Asteroids in Sector"),
            alt.Y("Hydro")
                .scale(domain=(0, 1500), nice=False)
                .axis(title="Hydrogen per Asteroid", values=[0, 300, 600, 900, 1200, 1500]),
            color="Status"
        )
    )

    rule = (
        alt.Chart(pd.DataFrame({"Max Hydro": [1500]}))
        .mark_rule(color="red")
        .encode(alt.Y("Max Hydro"))
    )

    return bar + rule

st.button("Simulate!", on_click=get_simulation)

st.warning("Warning: Crunch is currently unsupported by the mining simulation", icon="⚠️")

sim: Simulation = st.session_state["Simulation"]
inputs: UserInput = st.session_state["Inputs"]

if sim is not None and inputs is not None and sim.valid:
    log = sim.read_mining_progress_data()
    field = sim.read_hydro_field_data()

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
        icon="📝"
    )

    st.info(
        f"{log['Boosts'].values[-1]} artifact boosts mined at "
        f"{format_duration(log['Time'].values[-1])} DRS time",
        icon="📝"
    )

    time_min = 0
    time_max = log["Time"].values[-1]

    tab1, tab2 = st.tabs(["Interactive Graphs", "Animated Graphs"])

    with tab1:
        padding, slider_col = st.columns([1, 9])
        with slider_col:
            st.session_state["DRS Time"] = st.slider(
                "DRS Time (seconds)", min_value=time_min, max_value=time_max,
                step=10, format="%d", key="slider"
            )

        st.altair_chart(make_linechart(log, time=st.session_state["DRS Time"]), use_container_width=True)
        st.altair_chart(make_barchart(field, time=st.session_state["DRS Time"]), use_container_width=True)
    
    with tab2:
        col1, col2, col3 = st.columns([1, 1, 6])
        with col1:
            play_fast = st.button("Play (Fast)")
        with col2:
            play_slow = st.button("Play (Slow)")
        with col3:
            pbar = st.progress(0, text = f"DRS Time: {format_duration(time_min)}")
        line = st.altair_chart(make_linechart(log, time_min), use_container_width=True)
        bar = st.altair_chart(make_barchart(field, time_min), use_container_width=True)
    
        if play_fast or play_slow:
            for time in range(time_min, time_max + 10, 10):
                pbar.progress(time / time_max, text = f"DRS Time: {format_duration(time)}")
                line.altair_chart(make_linechart(log, time), use_container_width=True)
                bar.altair_chart(make_barchart(field, time), use_container_width=True)
                sleep(0.05 if play_fast else 0.2)
            # pbar.progress(0, text = f"DRS Time: {incr_to_dur(time)}")
elif sim is not None and inputs is not None:
    st.error(
        "Simulation failed to find a solution, please verify your inputs!"
    )
