from dataclasses import dataclass

import emoji
from blessed import Terminal
from halo import Halo


@dataclass
class Console:
    term = Terminal()
    log_level = "info"
    spinner = Halo(spinner="dots")

    def emoji(self, message):
        return emoji.emojize(message)

    def success(self, message):
        print(self.term.green("✔ " + message))

    def error(self, message):
        print(self.term.red(self.emoji(":multiply:  " + message)))

    def info(self, message):
        print(self.term.blue(self.emoji(":information:  " + message)))

    def warning(self, message):
        print(self.term.yellow(self.emoji(":warning:  " + message)))

    def debug(self, message):
        if self.log_level == "debug":
            print(self.term.magenta(self.emoji(":crystal_ball:  " + message)))

    def log(self, message):
        print(self.emoji(message))
