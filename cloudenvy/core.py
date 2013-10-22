# vim: tabstop=4 shiftwidth=4 softtabstop=4
import logging
import novaclient
import time

from cloudenvy.clouds import openstack
from cloudenvy import exceptions


class Envy(object):
    def __init__(self, config):
        self.config = config
        self.cloud_api = openstack.CloudAPI(self.config)
        self.name = config.project_config.get('name')

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
        if self.server():
            if not self._ip:
                self._ip = self.cloud_api.find_ip(self.server().id)
            return self._ip
        else:
            raise SystemExit('The ENVy you specified (`%s`) does not exist. '
                             'Try using the -n flag to specify an ENVy name.'
                             % self.name)

    def build_server(self):
        logging.info("Using image: %s" % self.config.image)
        try:
            image = self.cloud_api.find_image(self.config.image)
        except novaclient.exceptions.NoUniqueMatch:
            msg = ('There are more than one images named %s. Please specify '
                   'image id in your config.')
            raise SystemExit(msg % self.config.image)
        if not image:
            raise SystemExit('The image %s does not exist.' %
                             self.config.image)
        flavor = self.cloud_api.find_flavor(self.config.flavor)
        if not flavor:
            raise SystemExit('The flavor %s does not exist.' %
                             self.config.flavor)
        build_kwargs = {
            'name': self.name,
            'image': image,
            'flavor': flavor,
        }

        logging.info('Using security group: %s', self.config.sec_group_name)
        self._ensure_sec_group_exists(self.config.sec_group_name)
        build_kwargs['security_groups'] = [self.config.sec_group_name]

        if self.config.keypair_name is not None:
            logging.info('Using keypair: %s', self.config.keypair_name)
            self._ensure_keypair_exists(self.config.keypair_name,
                                        self.config.keypair_location)
            build_kwargs['key_name'] = self.config.keypair_name

        build_kwargs['meta'] = {}
        #TODO(gabrielhurley): Allow user-defined server metadata, see
        #https://github.com/cloudenvy/cloudenvy/issues/125 for more info.
        build_kwargs['meta']['os_auth_url'] = self.cloud_api.auth_url

        #TODO(jakedahn): Reintroduce this as a 'cloudconfigdrive' config flag.
        # if self.project_config['userdata_path']:
        #     userdata_path = self.project_config['userdata_path']
        #     logging.info('Using userdata from: %s', userdata_path)
        #     build_kwargs['user_data'] = userdata_path

        logging.info('Creating server...')
        server = self.cloud_api.create_server(**build_kwargs)

        server_id = server.id

        def server_ready(server):
            return server.status == 'ACTIVE'

        def fixed_ip_ready(server):
            return len(server.networks) > 0

        def floating_ip_ready(server):
            return bool(self.cloud_api.find_ip(server.id))

        def wait_for_condition(condition_func, fail_msg):
            for i in xrange(60):
                _server = self.cloud_api.get_server(server_id)
                if condition_func(_server):
                    return True
                else:
                    time.sleep(1)
            else:
                raise exceptions.Error(fail_msg)

        #NOTE(bcwaldon): fixed ips are actually assigned before
        # servers enter ACTIVE state in an OpenStack cloud
        wait_for_condition(fixed_ip_ready, 'Failed to assign fixed IP')

        wait_for_condition(server_ready, 'Server did not enter ACTIVE state')

        try:
            floating_ip = self.cloud_api.find_free_ip()
        except exceptions.NoIPsAvailable:
            logging.info('Allocating a new floating ip to project.')
            self.cloud_api.allocate_floating_ip()
            floating_ip = self.cloud_api.find_free_ip()

        logging.info('Assigning floating ip %s to server.', floating_ip)
        self.cloud_api.assign_ip(server, floating_ip)

        wait_for_condition(floating_ip_ready, 'Failed to assign floating IP')

    def _ensure_sec_group_exists(self, name):
        sec_group = self.cloud_api.find_security_group(name)

        if not sec_group:
            try:
                sec_group = self.cloud_api.create_security_group(name)
            except novaclient.exceptions.BadRequest:
                logging.error('Security Group "%s" already exists.' % name)

        if 'sec_groups' in self.config.project_config:
            rules = [tuple(rule.split(', ')) for rule in
                     self.config.project_config['sec_groups']]
        else:
            rules = [tuple(rule.split(', ')) for rule in
                     self.config.default_config['sec_groups']]
        for rule in rules:
            logging.debug('... adding rule: %s', rule)
            logging.info('Creating Security Group Rule %s' % str(rule))
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
        if not self.server():
            logging.error('Environment has not been created.\n'
                          'Try running `envy up` first?')
        else:
            logging.info('Creating snapshot %s...', name)
            self.cloud_api.snapshot(self.server(), name)
            logging.info('...done.')
            print name


class Command(object):

    def __init__(self, argparser, commands):
        self.commands = commands
        self._build_subparser(argparser)

    def _build_subparser(self, subparser):
        return subparser

    def run(self, config, args):
        return
