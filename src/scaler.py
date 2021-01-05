from logging import getLogger

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from config import ConfigLoader
from src.scraper import QueuesScraper


class WorkerScaler:

    def __init__(self, deployment_name):
        config.load_kube_config()
        self.logger = getLogger(self.__class__.__name__)
        self.v1 = client.AppsV1Api()
        self.rabbit_config = ConfigLoader()
        self.deployment_name = deployment_name
        self.scraper = QueuesScraper(deployment_name=deployment_name)

    def calculate_desired_pods(self, namespace='default'):
        """
        :param str namespace:
        :return: number of desired pods
        """
        deployment_properties = self.rabbit_config.get_deployment_properties(deployment_name=self.deployment_name)
        max_pod = deployment_properties['maxPod']
        queues = self.scraper.exclude_idle_queue_from_list()

        try:
            accumulative_limit = deployment_properties['accumulativeLimit']
        except KeyError:
            self.logger.info("accumulativeLimit not found in deployment %s config\nUsing default accumulativeLimit = 1"
                             % self.deployment_name)
            accumulative_limit = 1

        try:
            min_pod = deployment_properties['minPod']
        except KeyError:
            self.logger.info(
                "minPod not found in deployment %s config\nUsing default minPod = 0" % self.deployment_name)
            min_pod = 0

        current_pods = self.get_deployment_replicas(deployment_name=self.deployment_name, namespace=namespace)

        if not queues:
            self.logger.info(f"All queues are idle")
            if current_pods == min_pod:
                self.logger.info(f"current pods of {self.deployment_name} is min pods")
                return None
            else:
                self.logger.info(f"Scale {self.deployment_name} from {current_pods} to {min_pod}")
                return min_pod

        average_consumer_utilisation = self.scraper.get_queues_average_consumer_utilisation()

        desired_pods = current_pods
        if current_pods < min_pod:
            desired_pods = min_pod
        elif min_pod <= current_pods < max_pod:
            if average_consumer_utilisation < 0.9:
                desired_pods = current_pods + accumulative_limit
        elif current_pods >= max_pod:
            desired_pods = max_pod

        if desired_pods == current_pods == max_pod:
            self.logger.info(f"Current pods of {self.deployment_name} hit max threshold: {max_pod}")
            return None
        elif desired_pods == current_pods < max_pod:
            self.logger.info(f"Current pods of {self.deployment_name} are suitable: {current_pods}")
            return None
        else:
            self.logger.info(f"Scale {self.deployment_name} from {current_pods} to {desired_pods}")
            return desired_pods

    def set_deployment_replicas(self, deployment_name, namespace='default', replicas_number=1):
        """
        :param str deployment_name:
        :param str namespace:
        :param int replicas_number:
        :return: deployment body
        """
        body = self.v1.read_namespaced_deployment_scale(name=deployment_name, namespace=namespace)
        body.spec.replicas = replicas_number
        try:
            api_response = self.v1.patch_namespaced_deployment_scale(name=deployment_name, namespace=namespace,
                                                                     body=body)
            return api_response
        except ApiException as e:
            self.logger.error("Exception when calling AppsV1Api->patch_namespaced_deployment_scale: %s\n" % e)

    def get_deployment_replicas(self, deployment_name, namespace='default'):
        """
        :param str deployment_name:
        :param str namespace:
        :return: deployment replicas
        """
        try:
            body = self.v1.read_namespaced_deployment_scale(name=deployment_name, namespace=namespace)
            return body.status.replicas
        except ApiException as e:
            self.logger.error("Exception when calling AppsV1Api-->read_namespaced_deployment_scale: %s\n" % e)


if __name__ == '__main__':
    k8s = WorkerScaler(deployment_name='de-k8-harvesting-store-sa-posts-ins')
    pod_number = k8s.calculate_desired_pods()
    print(pod_number)
