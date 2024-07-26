from typing import Self

from pandas import DataFrame as df

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
    
    def set_strategy(self, mining_strategy: type[MiningStrategy]) -> Self:
        self._strategy = mining_strategy(self._inputs)
        return self
    
    def read_mining_progress_data(self) -> df:
        return self._strategy.read_mining_progress_data()
    
    def read_hydro_field_data(self) -> df:
        return self._strategy.read_hydro_field_data()
    
    def get_mining_delay(self) -> int:
        return self._strategy.get_mining_delay()
    
    def run(self) -> Self:
        try:
            self._valid = self._strategy.run()
        except AttributeError:
            self._valid = False
        return self
