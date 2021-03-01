import os
import re
import yaml


class ConfigLoader:

    def __init__(self):
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config.yml'))
        config_file = open(config_path)

        self.env_matcher = re.compile(r'(.*)\${([^}^{]+)}(.*)')
        yaml.add_implicit_resolver('!path', self.env_matcher, None, yaml.SafeLoader)
        yaml.add_constructor('!path', self.config_constructor, yaml.SafeLoader)

        self.parsed_config_file = yaml.load(config_file, Loader=yaml.SafeLoader)
        self.deployments = self.parsed_config_file['scaler']
        self.hosts = self.parsed_config_file['server']['hosts']
        self.username = self.parsed_config_file['server']['username']
        self.password = self.parsed_config_file['server']['password']

    def config_constructor(self, loader, node):
        value = node.value
        match = self.env_matcher.match(value)
        env_var = match.group(2)
        return match.group(1) + os.environ.get(env_var) + match.group(3)

    def get_deployments(self):
        deployment_list = []
        for deployment in self.deployments.keys():
            deployment_list.append(deployment)

        return deployment_list

    def get_deployment_properties(self, deployment_name):
        return self.parsed_config_file['scaler'][deployment_name]


if __name__ == '__main__':
    config = ConfigLoader()
    print(config.deployments)
