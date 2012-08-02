# vim: tabstop=4 shiftwidth=4 softtabstop=4
import logging

from cloudenvy import cloud
from cloudenvy import exceptions

class Template(object):
    def __init__(self, name, args, config):
        self.name = name
        self.config = config
        self.args = args
        section = 'template:%s' % args.template
        self.cloud_api = cloud.CloudAPI(args.cloud, self.config)
        self.image_name = config.get(section, 'image_name')
        self.flavor_name = config.get(section, 'flavor_name')
        self.assign_floating_ip = config.get(section, 'assign_floating_ip')
        self.sec_group_name = config.get(section, 'sec_group_name')
        self.keypair_name = config.get(section, 'keypair_name')
        self.keypair_location = config.get(section, 'keypair_location')
        self.remote_user = config.get(section, 'remote_user')
        self.userdata = config.get(section, 'userdata')
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
            raise exceptions.ImageNotFound()

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

        if self.args.provision:
            userdata_path = self.args.userdata or self.userdata
            logging.info('Using userdata from: %s', userdata_path)
            build_kwargs['user_data'] = userdata_path

        logging.info('Creating server...')
        server = self.cloud_api.create_server(**build_kwargs)

        # Wait for server to get fixed ip
        for i in xrange(600):
            server = self.cloud_api.get_server(server.id)
            if len(server.networks):
                break
            if i % 20:
                logging.info('...waiting for fixed ip')
            if i == 599:
                raise exceptions.FixedIPAssignFailure()
        logging.info('...done.')

        if self.assign_floating_ip:
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
                found_ip = self.cloud_api.find_ip(self.server.id)
                #server = self.cloud_api.get_server(server.id)
                if found_ip:
                    break
                if i % 5:
                    logging.info('...waiting for assigned ip')
                if i == 59:
                    raise exceptions.FloatingIPAssignFailur()
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

