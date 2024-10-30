import logging
import time
from utils.SteelSeriesLoggerHandler import SteelSeriesHandler, SsFormatter
import utils.mylogger as mylogger


def main():
    logging.setLoggerClass(mylogger.MyLogger)
    logger: mylogger.MyLogger = logging.getLogger("main")  # logger is just a fancy print that can send error to a file, over internet to any url, or in this case to your mouse
    logger.setLevel(logging.DEBUG)

    logger.addLevel(name="Blue", lvl=60, style={"color": 25})  # add some new fancy colored logger levels above level 50
    logger.addLevel("Gold", 70, {"color": 214})  # https://coloredlogs.readthedocs.io/en/latest/api.html#available-text-styles-and-colors
    logger.addLevel("Cuki", 80, {"color": "magenta"})
    logger.install()  # only needed if added some new colored levels afterwards

    SteelSeriesHandler.help()  # printing for troubleshooting
    print()  # empty separator line

    ssf = SsFormatter(  # the settings for steelseries app
        n_flashes=3,
        flash_freq=3,
        display_time=3000,
        device_type="rgb-1-zone",  # TODO Szia Gabor ezekre vagyok kivancsi
        device_zone="one",          # mit kell atallitani
        device_color_mode="color"   # https://github.com/SteelSeries/gamesense-sdk/blob/master/doc/api/standard-zones.md
    )

    # logger.debug(ssf.logcolor)

    # ssf.logcolor.update(      # if you wish to change the default level colors
    #     {50: (250, 0, 0)}     # there are levels from 10-50 (now added up to 80) every 10 steps
    # )

    ssh = SteelSeriesHandler()  # setup actual connection to the ss app
    ssh.setFormatter(ssf)  # optional
    logger.addHandler(ssh)  # add ss to logging output

    logger.info("SteelSeriesEngine is set up, i should blink green")
    time.sleep(2)
    logger.warning("Now yellow")
    time.sleep(2)
    logger.blue("Now Blue")

    while True:
        a = int(input("1-8 or 0:\n"))
        if a in range(1, 9):
            logger.log(level=a*10, msg="Hello")  # logger.log(20) is same as logger.info(); (10=debug,20=info,30=warning,40=error,50=critical)
        else:
            exit(0)


if __name__ == "__main__":  # pycharm shit
    main()
