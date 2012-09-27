# vim: tabstop=4 shiftwidth=4 softtabstop=4
import logging
import novaclient
import time

from cloudenvy import cloud
from cloudenvy import exceptions


class Envy(object):
    def __init__(self, config):
        self.name = config['project_config'].get('name')
        self.config = config
        self.user_config = config['cloudenvy']
        self.project_config = config['project_config']
        self.default_config = config['defaults']

        self.cloud_api = cloud.CloudAPI(self.config)
        self.image_name = self.project_config.get('image_name')
        self.image_id = self.project_config.get('image_id', None)
        self.flavor_name = self.project_config.get('flavor_name')
        self.remote_user = self.project_config.get('remote_user')
        self.auto_provision = self.project_config.get('auto_provision', False)

        self.keypair_name = self.user_config.get('keypair_name',
            self.default_config['keypair_name'])
        self.keypair_location = self.user_config.get('keypair_location',
            self.default_config['keypair_location'])
        self.sec_group_name = self.project_config.get('sec_group_name',
            self.default_config['sec_group_name'])
        self._server = None
        self._ip = None

    def list_servers(self):
        return self.cloud_api.list_servers()

    def find_server(self):
        return self.cloud_api.find_server(self.name)

    def delete_server(self):
        self.server().delete()
        self._server = None

    def server(self):
        if not self._server:
            self._server = self.find_server()
        return self._server

    def ip(self):
        if not self._ip:
            self._ip = self.cloud_api.find_ip(self.server().id)
        return self._ip

    def build_server(self):
        image = self.cloud_api.find_image(self.image_name, id=self.image_id)
        flavor = self.cloud_api.find_flavor(self.flavor_name)
        build_kwargs = {
            'name': self.name,
            'image': image,
            'flavor': flavor,
        }

        # TODO(jakedahn): security group name should be pulled from config.
        logging.info('Using security group: %s', self.sec_group_name)
        self._ensure_sec_group_exists(self.sec_group_name)
        build_kwargs['security_groups'] = [self.sec_group_name]

        if self.keypair_name is not None:
            logging.info('Using keypair: %s', self.keypair_name)
            self._ensure_keypair_exists(self.keypair_name,
                                        self.keypair_location)
            build_kwargs['key_name'] = self.keypair_name

        #TODO(jakedahn): Reintroduce this as a 'cloudconfigdrive' config flag.
        # if self.project_config['userdata_path']:
        #     userdata_path = self.project_config['userdata_path']
        #     logging.info('Using userdata from: %s', userdata_path)
        #     build_kwargs['user_data'] = userdata_path

        logging.info('Creating server...')
        server = self.cloud_api.create_server(**build_kwargs)

        # Wait for server to get fixed ip
        for i in xrange(600):
            server = self.cloud_api.get_server(server.id)
            if len(server.networks):
                break
            if i % 5:
                logging.info('...waiting for fixed ip')
            if i == 59:
                raise exceptions.FixedIPAssignFailure()
            time.sleep(1)

        logging.info('...done.')

        logging.info('Assigning a floating ip...')
        try:
            ip = self.cloud_api.find_free_ip()
        except exceptions.NoIPsAvailable:
            logging.info('...allocating a new floating ip')
            self.cloud_api.allocate_floating_ip()
            ip = self.cloud_api.find_free_ip()

        logging.info('...assigning %s', ip)
        self.cloud_api.assign_ip(server, ip)
        for i in xrange(60):
            logging.info('...finding assigned ip')
            found_ip = self.cloud_api.find_ip(self.server().id)
            #server = self.cloud_api.get_server(server.id)
            if found_ip:
                break
            if i % 5:
                logging.info('...waiting for assigned ip')
            if i == 59:
                raise exceptions.FloatingIPAssignFailur()
        logging.info('...done.')

    def _ensure_sec_group_exists(self, name):
        sec_group = self.cloud_api.find_security_group(name)

        if not sec_group:
            try:
                sec_group = self.cloud_api.create_security_group(name)
            except novaclient.exceptions.BadRequest:
                logging.error('Security Group "%s" already exists.' % name)

        if 'sec_groups' in self.project_config:
            rules = [tuple(rule.split(', ')) for rule in
                     self.project_config['sec_groups']]
        else:
            rules = [tuple(rule.split(', ')) for rule in
                     self.default_config['sec_groups']]
        for rule in rules:
            logging.debug('... adding rule: %s', rule)
            try:
                logging.info('Creating Security Group Rule %s' % str(rule))
                self.cloud_api.create_security_group_rule(sec_group, rule)
            except novaclient.exceptions.BadRequest:
                logging.info('Security Group Rule "%s" already exists.' %
                              str(rule))
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
        if not self.server():
            logging.error('Environment has not been created.\n'
                          'Try running `envy up` first?')
        else:
            logging.info('Creating snapshot %s...', name)
            self.cloud_api.snapshot(self.server(), name)
            logging.info('...done.')
            print name
