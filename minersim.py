from typing import Self

from pandas import DataFrame as df

from game_constants import *
from strategies import MiningStrategy
from userinput import UserInput


class Simulation:
    def __init__(self, inputs: UserInput) -> None:
        self._valid = False
        self._strategy = None
        self._inputs = inputs

    @property
    def valid(self) -> None:
        return self._valid
    
    def set_strategy(self, strat: MiningStrategy) -> Self:
        if strat == "Continuous Mining":
            self._strategy = ContinuousMining(self._inputs)
        return self
    
    def read_mining_progress_data(self) -> df:
        return self._strategy.read_mining_progress_data()
    
    def read_hydro_field_data(self) -> df:
        return self._strategy.read_hydro_field_data()
    
    def run(self) -> Self:
        try:
            self._valid = self._strategy.run()
        except AttributeError:
            self._valid = False
        return self
