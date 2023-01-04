from functools import cache
from json import load


@cache
def get_initial_board_state():
    with open('wargame/static/initial_state.json') as f:
        state = load(f)
        return state


months = (
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
)


def helper_functions():
    def turn_to_month(turn):
        return months[turn - 1]

    return dict(turn_to_month=turn_to_month)
