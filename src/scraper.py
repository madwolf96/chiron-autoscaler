from datetime import datetime, timedelta, timezone
from logging import getLogger

from fcache.cache import FileCache
from pyrabbit.api import Client, APIError

from config import ConfigLoader


class QueuesScraper:

    def __init__(self, deployment_name):
        self.logger = getLogger(self.__class__.__name__)
        self.deployment_name = deployment_name
        self.rabbit_config = ConfigLoader()
        self.queue_list_config = self.rabbit_config.get_deployment_properties(deployment_name=deployment_name)['queues']
        self.vhost_config = self.rabbit_config.get_deployment_properties(deployment_name=deployment_name)['vHost']
        self.queues_body = self.get_queues_body(vhost=self.vhost_config, queue_list=self.queue_list_config)

    def get_queues_body(self, vhost, queue_list):
        body_list = []
        host = self.get_rabbit_host_from_vhost(vhost)
        rabbit = self.rabbit_login(host)
        for queue in queue_list:
            body_list.append(rabbit.get_queue(vhost=vhost, name=queue))
        return body_list

    def total_messages(self):
        message_list = list()
        for body in self.exclude_idle_queue_from_list():
            message_list.append(body['messages'])
        return sum(message_list)

    def get_queues_average_consumer_utilisation(self):

        consumer_utilisation_list = []
        for queue_body in self.exclude_idle_queue_from_list():
            consumer_utilisation_list.append(queue_body['consumer_utilisation'])
        return sum(consumer_utilisation_list) / len(consumer_utilisation_list)

    def exclude_idle_queue_from_list(self):
        try:
            ttl = self.rabbit_config.get_deployment_properties(deployment_name=self.deployment_name)['ttl']
        except KeyError:
            self.logger.info("ttl not found in deployment %s config\nUsing default ttl = 1.0" % self.deployment_name)
            ttl = 1.0

        non_idle_queues_body = []
        for queue_body in self.queues_body:
            if self.check_queue_non_idling(queue_body=queue_body, ttl=ttl):
                non_idle_queues_body.append(queue_body)
        return non_idle_queues_body

    def check_queue_non_idling(self, queue_body, ttl):
        fmt = "%Y-%m-%d %H:%M:%S"

        if self.detect_stuck_messages_queue(queue_body=queue_body, ttl=ttl):
            return False

        try:
            idle_since = queue_body['idle_since']
            idle_since_time = datetime.strptime(idle_since, fmt)
            current_time = datetime.now(timezone.utc)
            current_time = current_time.replace(tzinfo=None)
            if timedelta.total_seconds(current_time - idle_since_time) / 60 > ttl and queue_body['consumers'] > 0:
                return False
            else:
                queue_body['consumer_utilisation'] = 0
                return True
        except KeyError:
            return True

    @staticmethod
    def detect_stuck_messages_queue(queue_body, ttl):
        past_queue = FileCache('message-queue', flag='cs')
        queue_name = queue_body['name']
        current_messages = queue_body['messages']
        current_consumers = queue_body['consumers']

        current_time = datetime.now(timezone.utc)
        current_time = current_time.replace(tzinfo=None)

        if past_queue.get(queue_name):
            time_range_minutes = timedelta.total_seconds(current_time - past_queue[queue_name]['time_catch']) / 60
            if past_queue[queue_name]['messages'] == current_messages:
                if time_range_minutes > ttl:
                    return True
                if time_range_minutes < ttl:
                    return False
            else:
                past_queue[queue_name] = {'messages': current_messages, 'time_catch': current_time,
                                          'consumers': current_consumers}
                return False
        else:
            past_queue[queue_name] = {'messages': current_messages, 'time_catch': current_time,
                                      'consumers': current_consumers}
            return False

    def get_rabbit_host_from_vhost(self, vhost, caching=True):
        if caching:
            vhost_host_cache = FileCache('vhost-host', flag='cs')
            if vhost_host_cache.get(vhost):
                return vhost_host_cache[vhost]
            else:
                vhost_host_cache[vhost] = self.get_host_action(vhost)
                return vhost_host_cache[vhost]
        else:
            return self.get_host_action(vhost)

    def rabbit_login(self, host):
        """
        :param str host:
        :return:
        """
        return Client(f'{host}:15672', self.rabbit_config.username, self.rabbit_config.password)

    def get_host_action(self, vhost):
        for host in self.rabbit_config.hosts:
            cl = Client(f'{host}:15672', self.rabbit_config.username, self.rabbit_config.password)
            try:
                cl.is_alive(vhost)
                return host
            except APIError:
                pass


if __name__ == '__main__':
    rabbit_client = QueuesScraper(deployment_name='de-k8-harvesting-relationship-tasks')
    for i in rabbit_client.exclude_idle_queue_from_list():
        print(i['name'])
