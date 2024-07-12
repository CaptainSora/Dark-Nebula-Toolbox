from collections import namedtuple
from datetime import datetime as dt

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
# "How to interpret results" section ("What does this mean?")
# Time spent breakdown (pie chart?)
#   Or horizontal bar chart (timeline?) that shows what's going on at each moment


VERSION = "0.3.0 (Beta)"


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

default("Miner Level", 6)

miner_img_paths = [f"Img/MS{x}.webp" for x in range(0, 8)]

module_inputs = [
    Module("Mining Boost", "MiningBoost", 0, 15, 11),
    Module("Remote Mining", "RemoteMining", 1, 15, 9),
    Module("Crunch", "Crunch", 0, 15, 0),
    Module("Genesis", "Genesis", 0, 15, 13),
    Module("Enrich", "Enrich", 0, 15, 11),
    Module("Artifact Boost", "ArtifactBoost", 1, 15, 13),
    Module("DRS Level", "RedStar", 7, 12, 10),
    Module("Miner Level", "", 1, 7, 6),
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
            with img:
                if mod.name == "Miner Level":
                    st.image(miner_img_paths[st.session_state["Miner Level"]])
                else:
                    st.image(f"Img/{mod.path}.webp")
            with field:
                module_values[modnum] = st.number_input(
                    mod.name, min_value=mod.min, max_value=mod.max, step=1, format="%d",
                    value=mod.init, key=mod.name, on_change=change_mod_levels)
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
default("field", None)


def get_simulation_results():
    if any([st.session_state[mod.name] is None for mod in module_inputs]):
        return
    st.session_state["output"], st.session_state["log"], st.session_state["field"] = simulate(
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


st.button("Simulate!", on_click=get_simulation_results)

st.warning("Warning: Crunch is currently unsupported by the mining simulation", icon="⚠️")

default("DRS Time", 10)

if st.session_state["output"] is not None and st.session_state["log"] is not None:
    st.write(st.session_state["output"])
    df = st.session_state["log"]

    if not df.empty:
        st.line_chart(
            data=df[["Time", "Total Hydro", "Max Hydro"]],
            x="Time", x_label="Time after 2nd genrich (seconds)",
            y_label="Hydrogen"
        )

        # st.session_state["DRS Time"] = st.slider(
        #     "DRS Time (seconds)", min_value=0, max_value=df["Time"].values[-1],
        #     value=0, step=10, format="%d", key="Bar Slider"
        # )
        # NB: Putting the slider after the bar chart led to a one tick delay

        # roid_cols = [f"r{x:02}" for x in range(1, 15)]

        # st.write(df[df["Time"] == st.session_state["DRS Time"]][roid_cols].T)

        # st.bar_chart(df[df["Time"] == st.session_state["DRS Time"]][roid_cols].T)


if st.session_state["field"] is not None:
    barfig = px.bar(
        st.session_state["field"], x="Roid", y=["Remaining", "Previous Enrich"],
        animation_frame="Time", range_y=[0, 1500])

    # Custom animation speed
    barfig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 120

    barfig.update_layout(
        title="Animated asteroid values",
        xaxis_title="Asteroids",
        yaxis_title="Hydrogen"
    )
    # TODO: change bar colors
    # TODO: add textures for currently draining roids?

    # TODO: Add hline for max amount
    # TODO: Add hline for re-enrich amount

    # TODO: fix legend names

    st.plotly_chart(barfig)

# wide_df = px.data.medals_wide()

# fig = px.bar(wide_df, x="nation", y=["gold", "silver", "bronze"], title="Wide-Form Input", )
# fig