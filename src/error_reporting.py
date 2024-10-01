from dataclasses import dataclass
from source import Location
from termcolor import *

@dataclass
class Message:
    location: Location
    comment: str


@dataclass
class Error:
    reason: Message
    messages: Message = None


class ErrorReport:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, err):
        self.errors.append(err)

    def warning(self, err):
        self.warnings.append(err)

    def has_errors(self):
        return len(self.errors) > 0

def print_error(error):
    print(format_error(error))

def print_warning(warning):
    print(format_warning(warning))

def print_error_report(report):
    for warning in report.warnings:
        print_warning(warning)
        print('\n')

    for error in report.errors:
        print_error(error)
        print('\n')


class Colorizer:
    def __init__(self, color):
        self.color = color

    def colored(self, text):
        return colored(text, self.color)


def format_error(error):
    colorizer = Colorizer("red")
    location = error.reason.location
    reason_line = colorizer.colored(f"error: {error.reason.comment}")
    reason_message = format_messages([Message(location, "")], colorizer)
    comments = format_messages(error.messages or [], Colorizer("cyan"))
    return reason_line + "\n" + reason_message + (("\n" + comments) if comments else "")


def format_warning(warning):
    colorizer = Colorizer("yellow")
    location = warning.reason.location
    reason_line = colorizer.colored(f"warning: {warning.reason.comment}")
    reason_message = format_messages([Message(location, "")], colorizer)
    comments = format_messages(warning.messages or [], Colorizer("cyan"))
    return reason_line + "\n" + reason_message + (("\n" + comments) if comments else "")


def format_messages(messages, squiggle_colorizer):
    if not messages:
        return ""
    line_digits = get_line_digits(messages)
    return "\n\n".join(format_message(message, squiggle_colorizer, line_digits) for message in messages)


def format_message(message, squiggle_colorizer, line_digits):
    location = location_text(message.location)
    if len(message_lines(message)) == 1:
        content = format_single_line_message(
            message, squiggle_colorizer, line_digits)
    else:
        content = format_multi_line_message(
            message, squiggle_colorizer, line_digits)

    return location + "\n" + content


def format_single_line_message(message, squiggle_colorizer, line_digits):
    '''
    If message location takes only one line then underline the code with
    squiggles
    ^^^^^^^^^
    '''
    location = message.location
    line_index, column_index = location.begin_line_and_column()
    line_index = location.begin_line()
    prefix = f"{line_index + 1:>{line_digits}} | "
    line = location.source.lines[line_index]
    underline_prefix = " " * (len(prefix) + column_index)
    underline = squiggle_colorizer.colored(underline_prefix + "^" * location.len())
    return prefix + line + "\n" + underline + (("\n" + message.comment) if message.comment else "")


def format_multi_line_message(message, squiggle_colorizer, line_digits):
    '''
      If message location takes more than one line then underline the code with
    /------------^^^^
    | vertical bars
    | and hyphens
    \\-^^^^^^^^^^^
    '''
    locations = message.location.split_lines()
    source_lines = [s.source.lines[s.begin_line()] for s in locations]
    first_underline = squiggle_colorizer.colored(
        "-" * locations[0].begin_column() + "^" * locations[0].len())
    last_underline = squiggle_colorizer.colored("^" * locations[-1].len())
    lines = [source_lines[0], first_underline] + \
        source_lines[1:] + [last_underline]

    for i in range(len(lines)):
        if i == 0:
            lines[i] = "  " + lines[i]
        elif i == 1:
            lines[i] = squiggle_colorizer.colored("/-") + lines[i]
        elif i == len(lines) - 1:
            lines[i] = squiggle_colorizer.colored("\\-") + lines[i]
        else:
            lines[i] = squiggle_colorizer.colored("| ") + lines[i]

    prefixes = [
        f"{s.begin_line() + 1:>{line_digits}} | "
        for s in locations
    ]

    prefixes = [prefixes[0]] + [" " * line_digits + " | "] + \
        prefixes[1:] + [" " * line_digits + " | "]
    for i, prefix in enumerate(prefixes):
        lines[i] = prefix + lines[i]

    code = "\n".join(lines)

    return code + (("\n" + message.comment) if message.comment else "")


def message_lines(message):
    return [s.begin_line() + 1 for s in message.location.split_lines()]


def get_line_digits(messages):
    lines = sum((message_lines(msg) for msg in messages), [])
    return len(str(max(lines)))


def location_text(location):
    line, column = location.begin_line_and_column()
    return f"--> file {location.source.name}, line {line + 1}, column {column + 1}"
