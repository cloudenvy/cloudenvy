# vim: tabstop=4 shiftwidth=4 softtabstop=4

import ConfigParser
import functools
import logging
import os
import os.path
import time

import fabric.api
import fabric.operations
import novaclient.exceptions
import novaclient.client


CONFIG_DEFAULTS = {
    'os_service_name': None,
    'os_region_name': None,
    'os_password': None,
    'assign_floating_ip': False,
    # NOTE(termie): not windows compatible
    'keypair_name': os.getlogin(),
    'keypair_location': os.path.expanduser('~/.ssh/id_rsa.pub'),
    'flavor_name': 'm1.large',
    'sec_group_name': 'default',
}


DEFAULT_ENV_NAME = 'cloudenvy'
SERVICE_NAME = os.environ.get('CLOUDENVY_SERVICE_NAME', DEFAULT_ENV_NAME)


def _get_config():
    config_file_location = os.environ.get('CLOUDENVY_CONFIG',
                                          os.path.expanduser('~/.cloudenvy'))
    logging.info('Loading config from: %s', config_file_location)
    config = ConfigParser.ConfigParser(CONFIG_DEFAULTS)
    config.read(config_file_location)

    logging.debug('Loaded config:')
    logging.debug('[%s]', SERVICE_NAME)
    for opt in config.options(SERVICE_NAME):
        logging.debug('  %s = %s', opt, config.get(SERVICE_NAME, opt))
    return config


class ImageNotFound(RuntimeError):
    pass


class SnapshotFailure(RuntimeError):
    pass


class FixedIPAssignFailure(RuntimeError):
    pass


class FloatingIPAssignFailure(RuntimeError):
    pass


class NoIPsAvailable(RuntimeError):
    pass


def not_found(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except novaclient.exceptions.NotFound:
            return None
    return wrapped


class CloudAPI(object):
    def __init__(self, config):
        self._client = None
        self.config = config
        self.user = self.config.get(SERVICE_NAME, 'OS_USERNAME')
        self.password = self.config.get(SERVICE_NAME, 'OS_PASSWORD')
        self.tenant_name = self.config.get(SERVICE_NAME, 'OS_TENANT_NAME')
        self.auth_url = self.config.get(SERVICE_NAME, 'OS_AUTH_URL')
        self.service_name = self.config.get(SERVICE_NAME, 'OS_SERVICE_NAME')
        self.region_name = self.config.get(SERVICE_NAME, 'OS_REGION_NAME')

    @property
    def client(self):
        if not self._client:
            self._client = novaclient.client.Client(
                    '2',
                    self.user,
                    self.password,
                    self.tenant_name,
                    self.auth_url,
                    service_name=self.service_name,
                    region_name=self.region_name,
            )
        return self._client

    @not_found
    def find_server(self, name):
        return self.client.servers.find(name=name)

    @not_found
    def get_server(self, server_id):
        return self.client.servers.get(server_id)

    def create_server(self, *args, **kwargs):
        return self.client.servers.create(*args, **kwargs)

    def find_free_ip(self):
        fips = self.client.floating_ips.list()
        for fip in fips:
            if not fip.instance_id:
                return fip.ip
        raise NoIPsAvailable()

    def find_ip(self, server_id):
        fips = self.client.floating_ips.list()
        for fip in fips:
            if fip.instance_id == server_id:
                return fip.ip

    def assign_ip(self, server, ip):
        server.add_floating_ip(ip)

    @not_found
    def find_image(self, name):
        return self.client.images.find(name=name)

    @not_found
    def get_image(self, image_id):
        return self.client.images.get(image_id)

    def snapshot(self, server, name):
        return self.client.servers.create_image(server, name)

    @not_found
    def find_flavor(self, name):
        return self.client.flavors.find(name=name)

    def find_security_group(self, name):
        try:
            return self.client.security_groups.find(name=name)
        except novaclient.exceptions.NotFound:
            return None

    def create_security_group(self, name):
        try:
            return self.client.security_groups.create(name, name)
        except novaclient.exceptions.NotFound:
            return None

    def create_security_group_rule(self, security_group, rule):
        return self.client.security_group_rules.create(
                security_group.id, *rule)

    def allocate_floating_ip(self):
        return self.client.floating_ips.create()

    @not_found
    def find_keypair(self, name):
        return self.client.keypairs.find(name=name)

    def create_keypair(self, name, key_data):
        return self.client.keypairs.create(name, public_key=key_data)


class Environment(object):
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.cloud_api = CloudAPI(self.config)
        self.image_name = config.get(SERVICE_NAME, 'image_name')
        self.flavor_name = config.get(SERVICE_NAME, 'flavor_name')
        self.assign_floating_ip = config.get(SERVICE_NAME, 'assign_floating_ip')
        self.sec_group_name = config.get(SERVICE_NAME, 'sec_group_name')
        self.keypair_name = config.get(SERVICE_NAME, 'keypair_name')
        self.keypair_location = config.get(SERVICE_NAME, 'keypair_location')
        self._server = None
        self._ip = None

    def find_server(self):
        return self.cloud_api.find_server(self.name)

    def delete_server(self):
        self.server.delete()
        self._server = None

    @property
    def server(self):
        if not self._server:
            self._server = self.find_server()
        return self._server

    @property
    def ip(self):
        if not self._ip:
            self._ip = self.cloud_api.find_ip(self.server.id)
        return self._ip

    def build_server(self):
        image = self.cloud_api.find_image(self.image_name)
        if not image:
            raise ImageNotFound()

        flavor = self.cloud_api.find_flavor(self.flavor_name)

        build_kwargs = {
            'name': self.name,
            'image': image,
            'flavor': flavor,
        }

        if self.sec_group_name is not None:
            logging.info('Using security group: %s', self.sec_group_name)
            self._ensure_sec_group_exists(self.sec_group_name)
            build_kwargs['security_groups'] = [self.sec_group_name]

        if self.keypair_name is not None:
            logging.info('Using keypair: %s', self.keypair_name)
            self._ensure_keypair_exists(self.keypair_name,
                                        self.keypair_location)
            build_kwargs['key_name'] = self.keypair_name

        logging.info('Creating server...')
        server = self.cloud_api.create_server(**build_kwargs)

        # Wait for server to get fixed ip
        for i in xrange(60):
            server = self.cloud_api.get_server(server.id)
            if len(server.networks):
                break
            if i % 5:
                logging.info('...waiting for fixed ip')
            if i == 59:
                raise FixedIPAssignFailure()
        logging.info('...done.')

        if self.assign_floating_ip:
            logging.info('Assigning a floating ip...')
            try:
                ip = self.cloud_api.find_free_ip()
            except NoIPsAvailable:
                logging.info('...allocating a new floating ip')
                self.cloud_api.allocate_floating_ip()
                ip = self.cloud_api.find_free_ip()

            logging.info('...assigning %s', ip)
            self.cloud_api.assign_ip(server, ip)
            for i in xrange(60):
                logging.info('...finding assigned ip')
                self.cloud_api.find_ip(self.server.id)
                server = self.cloud_api.get_server(server.id)
                if len(server.networks):
                    break
                if i % 5:
                    logging.info('...waiting for assigned ip')
                if i == 59:
                    raise FloatingIPAssignFailure()
            logging.info('...done.')

    def _ensure_sec_group_exists(self, name):
        if not self.cloud_api.find_security_group(name):
            logging.info('No security group named %s found, creating...', name)
            sec_group = self.cloud_api.create_security_group(name)

            rules = [
                ('icmp', -1, -1, '0.0.0.0/0'),
                ('tcp', 22, 22, '0.0.0.0/0'),
                ('tcp', 443, 443, '0.0.0.0/0'),
                ('tcp', 80, 80, '0.0.0.0/0'),
                ('tcp', 8080, 8080, '0.0.0.0/0'),
                ('tcp', 5000, 5000, '0.0.0.0/0'),
                ('tcp', 9292, 9292, '0.0.0.0/0'),
            ]
            for rule in rules:
                logging.debug('... adding rule: %s', rule)
                self.cloud_api.create_security_group_rule(sec_group, rule)
            logging.info('...done.')

    def _ensure_keypair_exists(self, name, pubkey_location):
        if not self.cloud_api.find_keypair(name):
            logging.info('No keypair named %s found, creating...', name)
            logging.debug('...using key at %s', pubkey_location)
            fap = open(pubkey_location, 'r')
            data = fap.read()
            logging.debug('...contents:\n%s', data)
            fap.close()
            self.cloud_api.create_keypair(name, data)
            logging.info('...done.')

    def snapshot(self, name):
        if not self.server:
            logging.error('Environment has not been created.\n'
                          'Try running `envy up` first?')
        else:
            logging.info('Creating snapshot %s...', name)
            self.cloud_api.snapshot(self.server, name)
            logging.info('...done.')
            print name


def provision(env=DEFAULT_ENV_NAME):
    """Manually provision a remote environment using a userdata script."""
    env = Environment(env, _get_config())
    logging.info('Provisioning environment.')
    remote_user = 'ubuntu'
    local_userdata_loc = os.environ.get('CLOUDENVY_USERDATA_LOCATION',
                                        './userdata')
    remote_userdata_loc = '~/userdata'
    with fabric.api.settings(host_string=env.ip,
                             user=remote_user,
                             forward_agent=True,
                             disable_known_hosts=True):
        for i in range(10):
            try:
                fabric.operations.put(local_userdata_loc,
                                      remote_userdata_loc,
                                      mode=0755)
                break
            except fabric.exceptions.NetworkError:
                time.sleep(1)

        fabric.operations.run(remote_userdata_loc)


def up(env=DEFAULT_ENV_NAME):
    """Create a server and show its IP."""
    env = Environment(env, _get_config())
    if not env.server:
        logging.info('Building environment.')
        try:
            env.build_server()
        except ImageNotFound:
            logging.error('Could not find image.')
            return
        except NoIPsAvailable:
            logging.error('Could not find free IP.')
            return
    if env.ip:
        print env.ip
    else:
        print 'Environment has no IP.'


def snapshot(env=DEFAULT_ENV_NAME, name=None):
    """Create a snapshot of a running server."""
    env = Environment(env, _get_config())
    env.snapshot(name or ('%s-snapshot' % env.name))


def ip(env=DEFAULT_ENV_NAME):
    """Show the IP of the current server."""
    env = Environment(env, _get_config())
    if not env.server:
        logging.error('Environment has not been created.\n'
                      'Try running `envy up` first?')
    elif env.ip:
        print env.ip
    else:
        logging.error('Could not find IP.')


def ssh(env=DEFAULT_ENV_NAME):
    """SSH into the current server."""
    env = Environment(env, _get_config())
    if env.ip:
        remote_user = 'ubuntu'
        disable_known_hosts = ('-o UserKnownHostsFile=/dev/null'
                               ' -o StrictHostKeyChecking=no')
        fabric.operations.local('ssh %s %s@%s' % (disable_known_hosts,
                                                  remote_user,
                                                  env.ip))
    else:
        logging.error('Could not find IP.')


def destroy(env=DEFAULT_ENV_NAME):
    """Power-off and destroy the current server."""
    env = Environment(env, _get_config())
    logging.info('Triggering environment deletion.')
    if env.find_server():
        env.delete_server()
        while env.find_server():
            logging.info('...waiting for server to be destroyed')
            time.sleep(1)
        logging.info('...done.')
    else:
        logging.error('No environment exists.')


COMMANDS = [up, provision, snapshot, ip, ssh]
