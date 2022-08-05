from dataclasses import dataclass
from os import environ

import emoji
import inquirer
from blessed import Terminal
from halo import Halo


class PromptTheme(inquirer.themes.Theme):
    def __init__(self):
        super().__init__()
        term = Terminal()
        self.Question.mark_color = term.blue
        self.Question.brackets_color = term.goldenrod1
        self.Question.default_color = term.blue

        self.Checkbox.selection_color = term.bold_goldenrod1
        self.Checkbox.selection_icon = "❯"
        self.Checkbox.selected_icon = "◉"
        self.Checkbox.unselected_icon = "◯"
        self.Checkbox.selected_color = term.seagreen2
        self.Checkbox.unselected_color = term.normal

        self.List.selection_color = term.bold_goldenrod1
        self.List.selection_cursor = "❯"
        self.List.unselected_color = term.normal


@dataclass
class Console:
    term = Terminal()
    log_level = "info"
    spinner = Halo(spinner="dots")

    def set_show_commands(self, b):
        self.show_commands = b

    def emoji(self, message):
        return emoji.emojize(message)

    def success(self, message):
        print(self.term.green("✔ " + message))

    def error(self, message):
        print(self.term.red(self.emoji("✖ " + message)))

    def info(self, message):
        print(self.term.blue(self.emoji(":information:  " + message)))

    def warning(self, message):
        print(self.term.yellow(self.emoji(":warning:  " + message)))

    def debug(self, message):
        if self.log_level == "debug":
            print(self.term.magenta(self.emoji(":crystal_ball:  " + message)))

    def log(self, message):
        print(self.emoji(message))

    def prompt(self, questions, theme=PromptTheme()):
        return inquirer.prompt(questions, theme=theme)

    def command(self, message):
        print(self.term.yellow("$ ") + self.term.blue(message))
