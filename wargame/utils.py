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
