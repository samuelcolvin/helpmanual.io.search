import logging
import logging.config


def setup_logging():
    """
    setup logging config for search by updating the arq logging config
    """
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'search.default': {
                'format': '%(levelname)s %(name)s: %(message)s',
            },
        },
        'handlers': {
            'search.default': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'search.default',
                'stream': 'ext://sys.stdout',
            },
        },
        'loggers': {
            'search': {
                'handlers': ['search.default'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
    logging.config.dictConfig(config)
