import streamlit as st
import numpy as np
import pandas as pd
from collections import namedtuple
from random import random

from minersim import simulate

st.title("DRS Mining Simulator")


def default(label, initvalue):
    if label not in st.session_state:
        st.session_state[label] = initvalue

Module = namedtuple("Module", ["name", "path", "min", "max"])

default("Miner Level", 6)

miner_img_paths = [f"Hades Star/Img/MS{x}.webp" for x in range(0, 8)]

module_inputs = [
    Module("Mining Boost", "MiningBoost", 0, 15),
    Module("Remote Mining", "RemoteMining", 1, 15),
    Module("Crunch", "Crunch", 0, 15),
    Module("Genesis", "Genesis", 0, 15),
    Module("Enrich", "Enrich", 0, 15),
    Module("Artifact Boost", "ArtifactBoost", 1, 15),
    Module("DRS Level", "RedStar", 7, 12),
    Module("Miner Level", "", 1, 7),
    Module("Miner Quantity", "MS6", 1, 4),
    Module("Target Number of Boosts", "ArtifactBoost", 1, 25)
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
                    st.image(f"Hades Star/Img/{mod.path}.webp")
            with field:
                module_values[modnum] = st.number_input(
                    mod.name, min_value=mod.min, max_value=mod.max, step=1, format="%d",
                    key=mod.name, on_change=change_mod_levels)
        modnum += 1

_, middle, _ = st.columns([1, 2, 1], gap="small")
with middle:
    img, field = st.columns([1, 5], vertical_alignment="center")
    mod = module_inputs[-1]
    with img:
        st.image(f"Hades Star/Img/{mod.path}.webp")
    with field:
        module_values[modnum] = st.number_input(
            mod.name, min_value=mod.min, max_value=mod.max, step=1, format="%d", key=mod.name)


default("output", None)
default("log", None)


def get_simulation_results():
    if any([st.session_state[mod.name] is None for mod in module_inputs]):
        return
    st.session_state["output"], st.session_state["log"] = simulate(
        st.session_state["DRS Level"],
        st.session_state["Genesis"],
        st.session_state["Enrich"],
        st.session_state["Artifact Boost"],
        st.session_state["Mining Boost"],
        st.session_state["Remote Mining"],
        st.session_state["Miner Level"],
        st.session_state["Miner Quantity"],
        st.session_state["Target Number of Boosts"]
    )


st.button("Simulate!", on_click=get_simulation_results)

st.warning("Warning: Crunch is currently unsupported by the mining simulation", icon="⚠️")

if st.session_state["output"] is not None and st.session_state["log"] is not None:
    st.write(st.session_state["output"])

    if not st.session_state["log"].empty:
        st.line_chart(
            data=st.session_state["log"][["Time", "Total Hydro", "Max Hydro"]],
            x="Time", x_label="Time after 2nd genrich (sconds)",
            y="Hydrogen"
        )

        st.bar_chart()

        st.session_state["time"] = st.slider("DRS Time")