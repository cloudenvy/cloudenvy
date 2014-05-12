# vim: tabstop=4 shiftwidth=4 softtabstop=4
import functools
import getpass
import logging
import time
import uuid

import novaclient.exceptions
import novaclient.client

from cloudenvy import exceptions

def not_found(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except novaclient.exceptions.NotFound:
            return None
    return wrapped


def bad_request(func):
    """decorator to wrap novaclient functions that may return a
    400 'BadRequest' exception when the endpoint is unavailable or
    unable to be resolved.
    """
    #novaclient.exceptions.BadRequest
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except novaclient.exceptions.BadRequest as xcpt:
            logging.error("Unable to communicate with endpoints: "
                          "Received 400/Bad Request from OpenStack: " +
                          str(xcpt))
            exit()
    return wrapped


def retry_on_overlimit(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except novaclient.exceptions.OverLimit as exc:
            retry_time = getattr(exc, 'retry_after', 0)
            if not retry_time:
                logging.fatal('Unable to allocate resource: %s' % exc.message)
                raise SystemExit()

            logging.debug('Request was limited, retrying in %s seconds: %s'
                          % (retry_time, exc.message))
            time.sleep(retry_time)

            try:
                return func(*args, **kwargs)
            except novaclient.exceptions.OverLimit as exc:
                logging.fatal('Unable to allocate resource: %s' % exc.message)
                raise SystemExit()

    return wrapped


class CloudAPI(object):
    def __init__(self, config):
        self._client = None
        self.config = config

        #NOTE(bcwaldon): This was just dumped here to make room for EC2.
        # Clean it up!
        for item in ['os_username', 'os_tenant_name', 'os_auth_url']:
            try:
                config.user_config['cloud'][item]
            except KeyError:
                raise SystemExit("Ensure '%s' is set in user config" % item)

        try:
            password = config.user_config['cloud']['os_password']
        except KeyError:
            username = config.user_config['cloud']['os_username']
            prompt = "Password for account '%s': " % username
            password = getpass.getpass(prompt)
            config.user_config['cloud']['os_password'] = password

        # OpenStack Auth Items
        self.user = self.config.user_config['cloud'].get('os_username', None)
        self.password = self.config.user_config['cloud'].get('os_password', None)
        self.tenant_name = self.config.user_config['cloud'].get('os_tenant_name',
                                                         None)
        self.auth_url = self.config.user_config['cloud'].get('os_auth_url', None)
        self.region_name = self.config.user_config['cloud'].get('os_region_name',
                                                         None)

    @property
    def client(self):
        if not self._client:
            self._client = novaclient.client.Client(
                '2',
                self.user,
                self.password,
                self.tenant_name,
                self.auth_url,
                no_cache=True,
                region_name=self.region_name)
        return self._client

    def is_server_active(self, server_id):
        server = self.get_server(server_id)
        return server.status == 'ACTIVE'

    def is_network_active(self, server_id):
        server = self.get_server(server_id)
        return len(server.networks) > 0

    @bad_request
    def list_servers(self):
        return self.client.servers.list()

    @bad_request
    @not_found
    def find_server(self, name):
        return self.client.servers.find(name=name)

    @bad_request
    @not_found
    def get_server(self, server_id):
        return self.client.servers.get(server_id)

    @retry_on_overlimit
    @bad_request
    def create_server(self, *args, **kwargs):
        kwargs.setdefault('meta', {})
        #TODO(gabrielhurley): Allow user-defined server metadata, see
        #https://github.com/cloudenvy/cloudenvy/issues/125 for more info.
        kwargs['meta']['os_auth_url'] = self.auth_url

        return self.client.servers.create(*args, **kwargs)

    def setup_network(self, server_id):
        server = self.get_server(server_id)

        try:
            floating_ip = self._find_free_ip()
        except exceptions.NoIPsAvailable:
            logging.info('Allocating a new floating ip to project.')
            self._allocate_floating_ip()
            floating_ip = self._find_free_ip()

        logging.info('Assigning floating ip %s to server.', floating_ip)
        self._assign_ip(server, floating_ip)

    @bad_request
    def _find_free_ip(self):
        fips = self.client.floating_ips.list()
        for fip in fips:
            if not fip.instance_id:
                return fip.ip
        raise exceptions.NoIPsAvailable()

    @bad_request
    def find_ip(self, server_id):
        fips = self.client.floating_ips.list()
        for fip in fips:
            if fip.instance_id == server_id:
                return fip.ip

    @retry_on_overlimit
    @bad_request
    def _assign_ip(self, server, ip):
        server.add_floating_ip(ip)

    @bad_request
    @not_found
    def find_image(self, search_str):
        try:
            return self.client.images.find(name=search_str)
        except novaclient.exceptions.NotFound:
            pass

        try:
            #NOTE(bcwaldon): We can't guarantee all images use UUID4 for their
            # image ID format, but this is the only way to get around issue
            # 69 (https://github.com/cloudenvy/cloudenvy/issues/69) for now.
            # Novaclient should really block us from requesting an image by
            # ID that's actually a human-readable name (with spaces in it).
            uuid.UUID(search_str)
            return self.client.images.get(search_str)
        except (ValueError, novaclient.exceptions.NotFound):
            raise SystemExit('Image `%s` could not be found.' % search_str)

    @retry_on_overlimit
    @bad_request
    def snapshot(self, server, name):
        return self.client.servers.create_image(server, name)

    @bad_request
    @not_found
    def find_flavor(self, name):
        return self.client.flavors.find(name=name)

    @bad_request
    @not_found
    def find_security_group(self, name):
        return self.client.security_groups.find(name=name)

    @retry_on_overlimit
    @bad_request
    @not_found
    def create_security_group(self, name):
        return self.client.security_groups.create(name, name)

    @retry_on_overlimit
    def create_security_group_rule(self, security_group, rule):
        try:
            return self.client.security_group_rules.create(
                security_group.id, *rule)
        except novaclient.exceptions.BadRequest:
            logging.info('Security Group Rule "%s" already exists.' %
                         str(rule))

    @retry_on_overlimit
    @bad_request
    def _allocate_floating_ip(self):
        return self.client.floating_ips.create()

    @bad_request
    @not_found
    def find_keypair(self, name):
        return self.client.keypairs.find(name=name)

    @retry_on_overlimit
    @bad_request
    def create_keypair(self, name, key_data):
        return self.client.keypairs.create(name, public_key=key_data)

    def delete_server(self, server):
        server.delete()
