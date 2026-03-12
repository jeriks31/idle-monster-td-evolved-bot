import logging


def setup_logger():
    # create a root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # set the level of this logger to the lowest level, debug.

    # create a file handler which logs even debug messages
    fh = logging.FileHandler('mylog.log')  # replace 'mylog.log' with your desired log file path
    fh.setLevel(logging.DEBUG)  # set the level of this handler to debug, which is the lowest level.

    # create a console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)  # set the level of this handler to info.

    # create formatters and add them to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
