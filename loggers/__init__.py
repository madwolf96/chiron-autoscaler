# Copyright (C) 2020 XOMAD. All rights reserved.
#
# Created on 2020-09-28

import logging
import os

from pythonjsonlogger.jsonlogger import JsonFormatter

DEFAULT_LOG_FORMATTER = '[%(asctime)s %(levelname)s] %(threadName)s/%(processName)s %(name)s | %(message)s'

FIELDS_SKIPPED = (
    'args', 'created', 'filename', 'funcName', 'exc_info', 'exc_text',
    'levelno', 'lineno', 'module', 'msecs', 'msg', 'pathname', 'process',
    'relativeCreated', 'stack_info', 'thread'
)
# Remaining fields: 'asctime', 'levelname', 'message', 'name', 'processName', 'threadName'
USE_JSON_LOG_FORMAT = True if os.getenv('USE_JSON_LOG_FORMAT') in \
                              ('True', 'true', 't', 'yes', 'y') else False

__loggers = {}


class GCloudJsonFormatter(JsonFormatter):
    """Custom JsonFormatter class that use special fields recognized by Google Cloud Logging.
    See: https://cloud.google.com/logging/docs/agent/configuration#process-payload
    """
    def process_log_record(self, log_record):
        log_record['time'] = log_record['timestamp']
        del log_record['timestamp']
        log_record['severity'] = log_record['levelname']
        del log_record['levelname']
        log_record['thread_name'] = log_record['threadName']
        del log_record['threadName']
        log_record['process_name'] = log_record['processName']
        del log_record['processName']
        return log_record


def get_logger(name, level=logging.INFO):
    global __loggers
    if name in __loggers:
        return __loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)
    sh = logging.StreamHandler()
    log_formatter = logging.Formatter(DEFAULT_LOG_FORMATTER) if not USE_JSON_LOG_FORMAT else \
        GCloudJsonFormatter(reserved_attrs=FIELDS_SKIPPED, timestamp=True)
    sh.setFormatter(log_formatter)
    logger.addHandler(sh)
    __loggers[name] = logger
    return logger
