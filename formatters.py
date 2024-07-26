from game_constants import MINUTE


def format_duration(time_in_seconds):
    return f"{time_in_seconds//MINUTE:02}m{time_in_seconds%MINUTE:02}s"
