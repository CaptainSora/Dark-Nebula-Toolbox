from collections import namedtuple
from datetime import datetime as dt
from time import sleep

import altair as alt
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from minersim import simulate

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
#   Co-ordinate colors between charts
# Change simulation output to a dict, save as a single session state variable
#   Also store a "valid" or "success" parameter for quick checks
# Animation:
#   Might have to give up and go with plotly
#   Alternatively: have an un-interactible animation, remove slider, use progress bar
#       Two tabs: interactive charts, animated charts
#       Use a loop to progressively rewrite the charts (reuse code?)


VERSION = "0.3.2 (Beta)"


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
    Module("Enrich", "Enrich", 0, 15, 11),
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

# def start_anim():
#     st.session_state["Anim"] = True
#     while st.session_state["Anim"] and st.session_state["DRS Time"] < 1000:
#         st.session_state.slider += 10
#         sleep(0.5)

# def stop_anim():
#     st.session_state["Anim"] = False

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

    st.session_state["DRS Time"] = st.slider(
        "DRS Time (seconds)", min_value=10, max_value=log["Time"].values[-1],
        step=10, format="%d", key="slider"
    )

    line = alt.Chart(log[["Time", "Total Hydro", "Max Hydro"]]).mark_line().encode(
        alt.X("Time").axis(title="Time after 2nd genrich (seconds)"),
        alt.Y("Total Hydro").axis(title="Total Hydrogen in Sector")
    )

    max_hydro = alt.Chart(pd.DataFrame({"y": [21000]})).mark_rule(color="light blue").encode(alt.Y("y"))
    cur_time = alt.Chart(pd.DataFrame({"x": [st.session_state["DRS Time"]]})).mark_rule(color="darkred").encode(alt.X("x"))

    st.altair_chart(line + max_hydro + cur_time, use_container_width=True)
    
    bar = alt.Chart(field[field["Time"] == st.session_state["DRS Time"]]).mark_bar().encode(
        alt.X("Roid").axis(labels=False, title="Asteroids in Sector"),
        alt.Y("Hydro").axis(title="Hydro", values=[0, 300, 600, 900, 1200, 1500]),
        color="Type"
    )

    rule = alt.Chart(pd.DataFrame({"y": [1500, st.session_state["enr_base"]]})).mark_rule(color="red").encode(alt.Y("y"))

    st.altair_chart(bar + rule, use_container_width=True)


    # if st.button("Play"):
    #     while st.session_state["DRS Time"] <= log["Time"].values[-1]:
    #         st.session_state["DRS Time"] = time_slider.slider(
    #             "DRS Time (seconds)", min_value=10, max_value=log["Time"].values[-1],
    #             value=st.session_state["DRS Time"]+10, step=10, format="%d"
    #         )
    #         bar_chart.altair_chart(bar + rule, use_container_width=True)
    #         sleep(0.5)


if False:
    # tab1, tab2 = st.tabs(["Altair bar chart", "Plotly bar chart"])
    # with tab1:
    df = st.session_state["field_long"]

    # st.write(df[df["Time"] == st.session_state["DRS Time"]])
    bar = alt.Chart(df[df["Time"] == st.session_state["DRS Time"]]).mark_bar().encode(
        alt.X("Roid").axis(labels=False),
        alt.Y("Hydro").scale(domain=(0, 1600)),
        color="Type"
    )

    rule = alt.Chart(pd.DataFrame({"y": [1500, st.session_state["enr_base"]]})).mark_rule(color="red").encode(y="y")

    st.altair_chart(bar + rule, use_container_width=True)

    # st.button("Play", on_click=start_anim)
    # st.button("Pause", on_click=stop_anim)
    # with tab2:
    #     barfig = px.bar(
    #         st.session_state["field_wide"], x="Roid", y=["Remaining", "Previous Enrich"],
    #         animation_frame="Time", range_y=[0, 1500])

    #     # Custom animation speed
    #     barfig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 120

    #     barfig.update_layout(
    #         title="Animated asteroid values",
    #         xaxis_title="Asteroids",
    #         yaxis_title="Hydrogen"
    #     )
    #     # TODO: change bar colors
    #     # TODO: add textures for currently draining roids?

    #     # TODO: Add hline for max amount
    #     # TODO: Add hline for re-enrich amount

    #     # TODO: fix legend names

    #     st.plotly_chart(barfig)
