import logging
import os
import signal
import time
from logging import getLogger
from multiprocessing import Process, Manager, Event

import gevent
from fcache.cache import FileCache
from kubernetes.client import ApiException

from config import ConfigLoader
from loggers import GCloudJsonFormatter, FIELDS_SKIPPED, DEFAULT_LOG_FORMATTER
from loggers import get_logger
from src.scaler import WorkerScaler

try:
    if os.getenv('LOGGING_LEVEL') is not None:
        logger = get_logger(name='', level=os.getenv('LOGGING_LEVEL'))
    else:
        logger = get_logger(name='')

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
            try:
                scaler = WorkerScaler(deployment_name=deployment_name)
                interval = self.config.get_deployment_properties(deployment_name=deployment_name)['interval']
                desired_pods = scaler.calculate_desired_pods()
                if desired_pods is None:
                    self.logger.info(f"Condition of deployment {deployment_name} no need to scale")
                else:
                    scaler.set_deployment_replicas(deployment_name=deployment_name, namespace=namespace,
                                                   replicas_number=desired_pods)
                # global ns
                # if ns.interrupted:
                #     self.logger.info("We done here! Bye Bye")
                #     break

                time.sleep(interval)
            except:
                time.sleep(30)
                self.scaling_deployment(deployment_name=deployment_name)

    def asynchronous(self):
        threads = [gevent.spawn(self.scaling_deployment, deployment) for deployment in self.config.get_deployments()]
        gevent.joinall(threads)

    def asynchronous_processing(self):
        deployments = []
        for deployment in self.config.get_deployments():
            p = Process(target=self.scaling_deployment, args=(deployment,))
            p.start()
            deployments.append(p)

        for p in deployments:
            p.join()


my_event = Event()


def signal_handler(received_signal, _):
    my_event.set()


if __name__ == '__main__':
    mgr = Manager()
    ns = mgr.Namespace()
    # ns.interrupted = False
    runner = ScaleRunner()
    signal.signal(signal.SIGTERM, signal_handler)

    for signame in (signal.SIGINT, signal.SIGTERM, signal.SIGQUIT):
        signal.signal(signame, signal_handler)
    
    # my_event.wait()
    runner.asynchronous_processing()
