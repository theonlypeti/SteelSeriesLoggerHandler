import itertools
import json
import logging, requests, asyncio
import os.path
import string
import coloredlogs
#import discord
import nextcord as discord
import urllib3.exceptions


class SteelSeriesHandler(logging.Handler):
    """
    A handler to light up your SteelSeries peripherals depending on the logEntry severity.
    The handler is async agnostic, meaning it will work in async and sync environments alike, non-blocking.

    :param engine_url: either the SteelSeries Engine local server ip:port, or the install location of the program eg. `C:/ProgramData/SteelSeries/` If not supplied, will try to find the default install location.
    :param name: Give your logger a custom name so it is human identifiable in the SteelSeries app.
    """
    #TODO very likely need to create a new game instead of just a new event as the "deinitialize_timer_length_ms": self.formatter.display_time is tied to the game
    game_name = "Python Logger"

    def __init__(self, engine_url: str = None, name: str = None):
        self._ok = False

        if engine_url:
            if engine_url.startswith("http"):
                self.url = engine_url
            elif engine_url.startswith("localhost") or engine_url.startswith("127"):
                self.url = os.path.join("http://", engine_url)
            else:
                self.read_url_from_file(engine_url)
        else:
            pd = os.getenv("PROGRAMDATA")  # this is for Windows users, linux users are tech-savvy enough to modify
            # this to their liking lol
            engine_url = os.path.join(pd, "SteelSeries", "SteelSeries Engine 3", "coreProps.json")
            self.read_url_from_file(engine_url)

        self.url = self.url.removesuffix("/")
        self.loop = None
        super().__init__()
        self.formatter: SsFormatter = SsFormatter()
        self.set_name(name or str(id(self))) #this calls setup_engine_event
        # self.setup_engine_event()

    def setFormatter(self, fmt: logging.Formatter):
        super().setFormatter(fmt)
        self.setup_engine_event()

    def set_name(self, name):
        remover = str.maketrans(string.punctuation, '_' * len(string.punctuation))
        name = name.translate(remover)
        name = name.upper().replace(" ", "_")
        self.remove_game()
        super().set_name(name)
        self.setup_engine_event()

    def format(self, record: logging.LogRecord):
        if record.levelno not in self.formatter.logcolor:
            self.formatter.getColor(record)
            self.setup_engine_event()

    @staticmethod
    def help():
        """If the log entries do not show up on your device, check if the game is not turned off in the SteelSeries Engine apps section.
        Next deselect any event type inside the game's color configuration screen (set to None), then disable and reenable the game.
        If you wish to change which zones should light up, or you do not own compatible devices with the preselected default zone, consult
        https://github.com/SteelSeries/gamesense-sdk/blob/master/doc/api/standard-zones.md and replace the `SsFormatter`'s parameters beginning with `device_*`."""
        print(SteelSeriesHandler.help.__doc__)

    async def post(self, logRecord: logging.LogRecord):
        self.format(record=logRecord)
        event_name = "LOG_ENTRY"
        payload = {
            "game": self.get_name(),
            "event": event_name,
            "data": {
                "value": logRecord.levelno  # Value between 0 and 100
            }
        }
        headers = {
            "Content-Type": "application/json"
        }
        try:
            requests.post(self.url + "/game_event", json=payload, headers=headers)
        except requests.exceptions.ConnectionError:
            pass
        except ConnectionRefusedError:
            print("SteelSeries engine port misconfigured?")

    def emit(self, record):
        """
        This function gets called when a log event gets emitted. It recieves a
        record, formats it and sends it to the url
        Parameters:
            record: a log record
        """
        if not self._ok:
            return
        el = asyncio.get_event_loop()
        if el.is_running():  # async env
            el.create_task(self.post(record))
        else:  # sync
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.post(record))
            # loop.run_in_executor(None, self.post, record) #dont worky
            # nor did run_forever
            self.loop = loop

    def read_url_from_file(self, engine_url):
        f = engine_url
        if os.path.isfile(f):
            with open(f, "r") as f:
                addr = json.load(f).get("address")
                if not addr:
                    raise IOError("No address found. SteelSeries engine misconfigured?")
        else:
            listdir = os.listdir(f)
            if "coreProps.json" not in listdir:
                if "GG" in listdir:
                    f = os.path.join(f, "GG")
                elif "SteelSeries Engine 3" in listdir:
                    f = os.path.join(f, "SteelSeries Engine 3")
                else:
                    raise IOError("Steelseries engine config not found!")
            listdir = os.listdir(f)
            if "coreProps.json" not in listdir:
                raise IOError("Steelseries engine config not found!")
            else:
                with open(os.path.join(f, "coreProps.json"), "r") as f:
                    addr = json.load(f).get("address")
                    if not addr:
                        raise IOError("No address found. SteelSeries engine misconfigured?")
        self.url = f"http://{addr}"

    def setup_engine_event(self) -> int:
        url = f"{self.url}/game_metadata"
        payload = {
            "game": self.get_name(),
            "game_display_name": f'Python Logger ({self.get_name()})',
            "developer": "theonlypeti",
            "deinitialize_timer_length_ms": self.formatter.display_time
        }
        headers = {
            "Content-Type": "application/json"
        }
        try:
            res = requests.post(url, json=payload, headers=headers)
            if res.status_code == 429:
                print("SteelSeries engine refused the connection. Error 429: Too Many Requests")
                return res.status_code
        except (urllib3.exceptions.MaxRetryError, ConnectionRefusedError, requests.exceptions.ConnectionError, urllib3.exceptions.NewConnectionError) as e:
            print("SteelSeries engine port either misconfigured or the app is not running in the background.", e.__class__, str(e), sep="\n")
            return 404

        url = f"{self.url}/bind_game_event"
        device_type = self.formatter.device_type
        device_zone = self.formatter.device_zone
        device_color_mode = self.formatter.device_color_mode

        rate_dict = {
            "frequency": [
                {
                    "low": self.formatter.flash_above_level,
                    "high": 100,
                    "frequency": self.formatter.flash_freq,
                    "repeat_limit": self.formatter.n_flashes

                }
            ]
        }

        color_stages_list = []
        lvl = -1
        levels = list(sorted(list(self.formatter.logcolor.keys())))
        for prev, lvl in itertools.pairwise([-1] + levels):
            r, g, b = self.formatter.logcolor[lvl]
            color_stages_list.append({
                "low": prev+1,
                "high": lvl,
                "color":
                    {"red":r, "green":g, "blue": b}
            })
        color_stages_list.append({"low":lvl+1, "high":100, "color":{"red":255, "green":255, "blue":255}})

        payload = {
            "game": self.get_name() ,
            "event": "LOG_ENTRY",
            "min_value": 0,
            "max_value": 100,
            "icon_id": 31,
            "handlers": [
                {
                    "device-type": device_type,
                    "zone": device_zone,
                    "mode": device_color_mode,
                    "rate": rate_dict,
                    "color": color_stages_list
                    }
            ]
        }
        headers = {
            "Content-Type": "application/json"
        }
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            self._ok = True
        return res.status_code

    def close(self):
        self.remove_game()

    def remove_game(self):
        url = f"{self.url}/remove_game"
        payload = {
            "game": self.get_name()
        }
        headers = {
            "Content-Type": "application/json"
        }
        requests.post(url, json=payload, headers=headers)
        if self.loop:
            if self.loop.is_running():
                self.loop.close()


class SsFormatter(logging.Formatter):
    """
    Subclassed logging Formatter to format and setup the python game/app in SteelSeries Engine

    :ivar logcolor: A dict of log level num: rgb tuple representation of color. If you've added new levels, the formatter will try to guess the color, if the 'coloredlogs.DEFAULT_LEVEL_STYLES' dict is updated to reflect the level styles. Unknown level colors default to white.
    You may update the `self.logcolor` dict with your desired keys and values.
    :ivar display_time: How many milliseconds to show color for
    :ivar flash_freq: Flashing frequency in Hz
    :ivar n_flashes: How many times to flash (Might not always work after changing config)
    :ivar flash_above_level: Log entries below (exclusive) this numerical level will not flash, only light up
    """
    def __init__(self, **kwargs):
        super().__init__()
        self.display_time: int = 3000
        self.device_type = "rgb-1-zone"
        self.device_zone = "one"
        self.device_color_mode = "color"
        self.flash_freq: int = 2
        self.n_flashes: int = 3
        self.flash_above_level: int = 0
        self.logcolor: dict[int, tuple[int, int, int]] = {
            10: (50,50,50),
            20: (0,150,0),
            30: (255,255,0),
            40: (100,0,0),
            50: (255,0,0)
        }
        for k, v in kwargs.items():
            setattr(self, k, v)

    def format(self, logRecord: logging.LogRecord) -> None:
        """there is not much to format tbh"""
        pass

    def getColor(self, logRecord: logging.LogRecord) -> None:  # TODO lose dependency on discord?
        """Collects colors and updates the SteelSeries Engine game event.
         If the log level is not one of the defaults, tries to guess based on the 'coloredlogs.DEFAULT_LEVEL_STYLES' dict."""
        clr = self.logcolor.get(logRecord.levelno)
        if clr is None:
            try:  # try and convert the level color from the coloredlogs styles to discord colors
                colorname = coloredlogs.DEFAULT_LEVEL_STYLES.get(logRecord.levelname.lower()).get("color")
                if colorname == "white":
                    clr = discord.Color(16777215)
                elif colorname == "black":
                    clr = discord.Color(0)
                else:
                    clr = getattr(discord.Color, colorname)()
            except Exception:
                try:  # what if the level name is the color, I'm known to name them that way (logger.blue/gold()) lol
                    clr = getattr(discord.Color, logRecord.levelname.lower())()
                except Exception:
                    print(f"Could not initialize {logRecord.levelno} level color. Using default white.")

            finally:
                self.logcolor.update({logRecord.levelno: clr.to_rgb()})
