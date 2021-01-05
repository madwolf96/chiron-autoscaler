import logging
import os
import signal
from logging import getLogger

import gevent
from fcache.cache import FileCache
from loggers import GCloudJsonFormatter, FIELDS_SKIPPED, DEFAULT_LOG_FORMATTER
from loggers import get_logger

from config import ConfigLoader
from src.scaler import WorkerScaler

logger = get_logger(name='')
try:
    if os.getenv('KUBERNETES_SERVICE_HOST') is not None:
        for handler in logger.handlers:
            handler.setFormatter(GCloudJsonFormatter(reserved_attrs=FIELDS_SKIPPED, timestamp=True))
    else:
        for handler in logger.handlers:
            handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMATTER))
except KeyError:
    pass


class ScaleRunner:

    def __init__(self):

        self.config = ConfigLoader()
        self.interval = FileCache('interval', flag='cs')
        self.logger = getLogger(name=self.__class__.__name__)

    def scaling_deployment(self, deployment_name, namespace='default'):
        """
        :param str deployment_name:
        :param str namespace:
        :return:
        """
        while True:
            scaler = WorkerScaler(deployment_name=deployment_name)
            interval = self.config.get_deployment_properties(deployment_name=deployment_name)['interval']
            desired_pods = scaler.calculate_desired_pods()
            if desired_pods is None:
                self.logger.info(f"Condition of deployment {deployment_name} no need to scale")
            else:
                scaler.set_deployment_replicas(deployment_name=deployment_name, namespace=namespace,
                                               replicas_number=desired_pods)

            if interrupted:
                self.logger.info("We done here! Bye Bye")
                break

            gevent.sleep(interval)

    def asynchronous(self):
        threads = [gevent.spawn(self.scaling_deployment, deployment) for deployment in self.config.get_deployments()]
        gevent.joinall(threads)


def signal_handler(signal, frame):
    global interrupted
    interrupted = True


if __name__ == '__main__':
    interrupted = False
    runner = ScaleRunner()
    signal.signal(signal.SIGTERM, signal_handler)
    runner.asynchronous()
