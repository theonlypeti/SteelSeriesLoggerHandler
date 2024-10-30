import logging
from functools import partialmethod
import coloredlogs
# from utils.DiscordWebhookLoggerHandler import WebhookHandler, WhFormatter
# from utils.SteelSeriesLoggerHandler import SteelSeriesHandler, SsFormatter


class MyLogger(logging.Logger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def addLevel(cls, name, lvl, style):
        setattr(cls, name.lower(), partialmethod(cls._anyLog, lvl))
        logging.addLevelName(lvl, name)
        coloredlogs.DEFAULT_LEVEL_STYLES.update({name.lower(): style})

    def _anyLog(self, level, message, *args, **kwargs):
        if self.isEnabledFor(level):
            self._log(level, message, args, **kwargs)

    def __call__(self, message, *args, **kwargs):
        if self.isEnabledFor(logging.INFO):
            self._log(logging.INFO, message, args, **kwargs)

    def install(self):
        coloredlogs.install(level=self.getEffectiveLevel(), logger=self, fmt=FORMAT, style="{")


FORMAT = "[ {asctime} {name} {filename} {lineno} {funcName}() {levelname} ] {message}"
formatter = logging.Formatter(FORMAT, style="{")
coloredlogs.DEFAULT_FIELD_STYLES = {'asctime': {'color': 100}, 'lineno': {'color': 'magenta'}, 'levelname': {'bold': True, 'color': 'black'}, 'filename': {'color': 25}, 'name': {'color': 'blue'}, 'funcname': {'color': 'cyan'}}
coloredlogs.DEFAULT_LEVEL_STYLES = {'critical': {'bold': True, 'color': 'red'}, 'debug': {'bold': True, 'color': 'black'}, 'error': {'color': 'red'}, 'info': {'color': 'green'}, 'notice': {'color': 'magenta'}, 'spam': {'color': 'green', 'faint': True}, 'success': {'bold': True, 'color': 'green'}, 'verbose': {'color': 'blue'}, 'warning': {'color': 'yellow'}}

logging.setLoggerClass(MyLogger)

# https://coloredlogs.readthedocs.io/en/latest/api.html#available-text-styles-and-colors