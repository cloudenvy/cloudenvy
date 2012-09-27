# vim: tabstop=4 shiftwidth=4 softtabstop=4
import functools
import exceptions
import logging

import novaclient.exceptions
import novaclient.client


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
        self.user_config = config['cloudenvy']
        self.project_config = config['project_config']

        # OpenStack Auth Items
        self.user = self.user_config['cloud'].get('os_username', None)
        self.password = self.user_config['cloud'].get('os_password', None)
        self.tenant_name = self.user_config['cloud'].get('os_tenant_name',
                                                         None)
        self.auth_url = self.user_config['cloud'].get('os_auth_url', None)

    @property
    def client(self):
        if not self._client:
            self._client = novaclient.client.Client(
                '2',
                self.user,
                self.password,
                self.tenant_name,
                self.auth_url)
        return self._client

    def list_servers(self):
        return self.client.servers.list()

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
        raise exceptions.NoIPsAvailable()

    def find_ip(self, server_id):
        fips = self.client.floating_ips.list()
        for fip in fips:
            if fip.instance_id == server_id:
                return fip.ip

    def assign_ip(self, server, ip):
        server.add_floating_ip(ip)

    @not_found
    def find_image(self, name, id=None):
        if id:
            try:
                image = self.client.images.get(id)
            except novaclient.exceptions.NotFound:
                logging.error('Image with the id of `%s` Not Found' % id)
                exit()
        else:
            try:
                image = self.client.images.find(name=name)
            except novaclient.exceptions.NotFound:
                logging.error('Image `%s` Not Found' % name)
                exit()
            except novaclient.exceptions.NoUniqueMatch:
                logging.error('There are multiple images named `%s` stored in '
                              'Glance. To continue you should define '
                              '`image_id` in your project\'s Envyfile.' % name)
                exit()
        return image

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
