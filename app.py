from collections import namedtuple
from datetime import datetime as dt
from time import sleep

import altair as alt
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from minersim import simulate, incr_to_dur

# TODO:
# Tab icon
# Page menu
#   Help: maybe an email link or google form?
#   Bug: Google form
#   About: Discord contact
# Sanity check miner lv vs AB lv
# Learn about crunch mechanics
# Start timer at start of DRS
#   Take input on when first genrich is?
#   Need an enrich timer as well
# Help text on inputs
# Below Line chart, show actions at current time step? (Link to slider)
# Add warning text about random roids, to simulate a few times and take the 
#   latest start time
# Explain simulation assumptions
#   e.g. mining method, "safe" h amount (no roid at 0 as a built in safety margin)
# Change text output to have timestamps for each event
#   Maybe this is the instructions section?
#   "Miners are currently..."
# "How to interpret results" section ("What does this mean?")
# Time spent breakdown (pie chart?)
#   Or horizontal bar chart (timeline?) that shows what's going on at each moment
# Setup breakdown ("Why these starting roids")
# Bar chart:
#   Rename "Type" to "Legend" or something useful
#   Add 3rd type to differentiate currently draining and not draining
# Line chart:
#   Add "previous enrich" line similar to the bar chart?
#       Counterargument: pointless horizontal lines at peaks
#   Co-ordinate colors between charts
#   Change x-axis to be a duration?
# Change simulation output to a dict, save as a single session state variable
#   Also store a "valid" or "success" parameter for quick checks
# Animation:
#   Might have to give up and go with plotly
#   Alternatively: have an un-interactible animation, remove slider, use progress bar
#       Two tabs: interactive charts, animated charts
#       Use a loop to progressively rewrite the charts (reuse code?)
# Feature:
#   Compare final time against two builds
#   Find out most time-efficient next upgrade


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
    Module("Target Number of Artifact Boosts", "ArtifactBoost", 1, 25, 18)
]

def change_mod_levels():
    pass

module_values = [None for _ in module_inputs]

modnum = 0

### Inputs
for _ in range(3):
    for col in st.columns(3, gap="medium"):
        with col:
            img, field = st.columns([1, 3], vertical_alignment="center")
            mod = module_inputs[modnum]
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
        modnum += 1

_, middle, _ = st.columns([1, 2, 1], gap="small")
with middle:
    img, field = st.columns([1, 5], vertical_alignment="center")
    mod = module_inputs[-1]
    with img:
        st.image(f"Img/{mod.path}.webp")
    with field:
        module_values[modnum] = st.number_input(
            mod.name, min_value=mod.min, max_value=mod.max, step=1, format="%d",
            value=mod.init, key=mod.name, on_change=change_mod_levels)


default("output", None)
default("log", None)
default("field_wide", None)
default("field_long", None)

default("DRS Time", 10)

default("Anim", False)


def get_simulation_results():
    if any([st.session_state[mod.name] is None for mod in module_inputs]):
        return
    (
        st.session_state["output"],
        st.session_state["log"],
        st.session_state["field_wide"],
        st.session_state["field_long"],
        st.session_state["enr_base"]
    ) = simulate(
        st.session_state["DRS Level"],
        st.session_state["Genesis"],
        st.session_state["Enrich"],
        st.session_state["Artifact Boost"],
        st.session_state["Mining Boost"],
        st.session_state["Remote Mining"],
        st.session_state["Miner Level"],
        st.session_state["Miner Quantity"],
        st.session_state["Target Number of Artifact Boosts"]
    )

def make_linechart(log, time):
    line = alt.Chart(log[["Time", "Total Hydro", "Max Hydro"]]).mark_line().encode(
        alt.X("Time")
            .scale(domain=(10, log["Time"].values[-1]), nice=False)
            .axis(title="Time after 2nd genrich (seconds)"),
        alt.Y("Total Hydro") \
            .scale(domain=(0, 21000), nice=False) \
            .axis(title="Total Hydrogen in Sector",)
    )

    max_hydro = alt.Chart(pd.DataFrame({"y": [21000]})).mark_rule(color="red").encode(alt.Y("y"))
    cur_time = alt.Chart(pd.DataFrame({"x": [time]})).mark_rule(color="orange").encode(alt.X("x"))

    return line + max_hydro + cur_time

def make_barchart(field, time):
    bar = alt.Chart(field[field["Time"] == time]).mark_bar().encode(
        alt.X("Roid").axis(labels=False, title="Asteroids in Sector"),
        alt.Y("Hydro").axis(title="Hydro", values=[0, 300, 600, 900, 1200, 1500]),
        color="Type"
    )

    rule = alt.Chart(pd.DataFrame({"y": [1500, st.session_state["enr_base"]]})).mark_rule(color="red").encode(alt.Y("y"))

    return bar + rule

st.button("Simulate!", on_click=get_simulation_results)

st.warning("Warning: Crunch is currently unsupported by the mining simulation", icon="⚠️")

if all([
        st.session_state["output"] is not None,
        st.session_state["log"] is not None,
        st.session_state["field_long"] is not None
    ]):
    st.write(st.session_state["output"])
    log = st.session_state["log"]
    field = st.session_state["field_long"]

    time_min = 10
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
            pbar = st.progress(0, text = f"DRS Time: {incr_to_dur(time_min)}")
        line = st.altair_chart(make_linechart(log, time_min), use_container_width=True)
        bar = st.altair_chart(make_barchart(field, time_min), use_container_width=True)
    
        if play_fast or play_slow:
            for time in range(time_min, time_max + 10, 10):
                pbar.progress(time / time_max, text = f"DRS Time: {incr_to_dur(time)}")
                line.altair_chart(make_linechart(log, time), use_container_width=True)
                bar.altair_chart(make_barchart(field, time), use_container_width=True)
                sleep(0.05 if play_fast else 0.2)
            # pbar.progress(0, text = f"DRS Time: {incr_to_dur(time)}")
