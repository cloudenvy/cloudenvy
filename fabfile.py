import os
import os.path
import time

import fabric.api
import fabric.operations
import novaclient.exceptions
import novaclient.client


remote_user = os.environ.get('CE_USER', 'ubuntu')
fabric.api.env.user = remote_user
DEFAULT_ENV_NAME = 'cloudenvy'
userdata_location = os.environ.get('CE_USERDATA_LOCATION', './userdata')




class ImageNotFound(RuntimeError):
    pass


class SnapshotFailure(RuntimeError):
    pass


class FixedIPAssignFailure(RuntimeError):
    pass


class NoIPsAvailable(RuntimeError):
    pass


class CloudAPI(object):
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if not self._client:
            self._client = novaclient.client.Client(
                    '2',
                    os.environ.get('OS_USERNAME'),
                    os.environ.get('OS_PASSWORD'),
                    os.environ.get('OS_TENANT_NAME'),
                    os.environ.get('OS_AUTH_URL'),
                    service_type='compute',
            )

        return self._client

    def find_server(self, name):
        try:
            return self.client.servers.find(name=name)
        except novaclient.exceptions.NotFound:
            return None

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

    def find_image(self, name):
        try:
            return self.client.images.find(name=name)
        except novaclient.exceptions.NotFound:
            return None

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

    def find_keypair(self, name):
        try:
            return self.client.keypairs.find(name=name)
        except novaclient.exceptions.NotFound:
            return None

    def create_keypair(self, name, key_data):
        return self.client.keypairs.create(name, public_key=key_data)


class Environment(object):
    def __init__(self, name):
        self.name = name
        self.cloud_api = CloudAPI()
        self._server = None
        self._ip = None

    @property
    def server(self):
        return self.cloud_api.find_server(self.name)

    def build_server(self):
        image_name = os.environ.get('CE_IMAGE_NAME',
                                    'precise-server-cloudimg-amd64')
        image = self.cloud_api.find_image(image_name)
        if not image:
            raise ImageNotFound()

        flavor_name = os.environ.get('CE_FLAVOR_NAME', 'm1.large')
        flavor = self.cloud_api.find_flavor(flavor_name)

        sec_group_name = os.environ.get('CE_SEC_GROUP_NAME', 'cloudenvy')
        self._ensure_sec_group_exists(sec_group_name)

        keypair_name = os.environ.get('CE_KEY_NAME', 'cloudenvy')
        self._ensure_keypair_exists(keypair_name)

        build_kwargs = {
            'name': self.name,
            'image': image,
            'flavor': flavor,
            'key_name': keypair_name,
            'security_groups': [sec_group_name],
        }
        server = self.cloud_api.create_server(**build_kwargs)

        # Wait for server to get fixed ip
        for i in xrange(60):
            server = self.cloud_api.get_server(server.id)
            if len(server.networks):
                break
            if i == 59:
                raise FixedIPAssignFailure()

        ip = self.cloud_api.find_free_ip()
        self.cloud_api.assign_ip(server, ip)

    def _ensure_sec_group_exists(self, name):
        if not self.cloud_api.find_security_group(name):
            sec_group = self.cloud_api.create_security_group(name)

            rules = [
                ('icmp', -1, -1, '0.0.0.0/0'),
                ('tcp', 22, 22, '0.0.0.0/0'),
                ('tcp', 8080, 8080, '0.0.0.0/0'),
            ]
            for rule in rules:
                self.cloud_api.create_security_group_rule(sec_group, rule)

    def _ensure_keypair_exists(self, name):
        if not self.cloud_api.find_keypair(name):
            pubkey_location = os.environ.get('CE_KEY_LOCATION',
                    os.path.expanduser('~/.ssh/id_rsa.pub'))
            fap = open(pubkey_location, 'r')
            data = fap.read()
            fap.close()
            self.cloud_api.create_keypair(name, data)

    @property
    def ip(self):
        return self.cloud_api.find_ip(self.server.id)



def provision(env=DEFAULT_ENV_NAME):
    env = Environment(env)
    print 'Provisioning environment.'
    with fabric.api.settings(host_string=env.ip):
        for i in range(10):
            try:
                fabric.operations.put(userdata_location, '~', mode=0755)
                break
            except fabric.exceptions.NetworkError:
                time.sleep(1)
                pass

        fabric.operations.run(userdata_location)


def up(env=DEFAULT_ENV_NAME):
    env = Environment(env)
    if not env.server:
        print 'Building environment.'
        try:
            env.build_server()
        except ImageNotFound:
            print 'Could not find image.'
            return
        except NoIPsAvailable:
            print 'Could not find free IP.'
            return
    if env.ip:
        print 'Environment IP: %s.' % env.ip
    else:
        print 'Environment has no IP.'


def backup(env=DEFAULT_ENV_NAME, image_name=None):
    client = _get_nova_client()
    server = _find_server(client, env)
    if not server:
        print 'Environment not found.'
    else:
        print 'Triggering image creation.'
        image_name = image_name or ('%s-backup' % env)
        image_id = server.create_image(image_name)
        # Wait for image to become available
        for i in xrange(60):
            image = client.images.get(image_id)
            if image.status == 'ACTIVE':
                break
            if i == 59:
                raise SnapshotFailure()

        print 'Created environment snapshot: %s.' % image_name


def ip(env=DEFAULT_ENV_NAME):
    env = Environment(env)
    if not env.server:
        print 'Environment has not been created'
    elif env.ip:
        print 'Environment IP: %s' % env.ip
    else:
        print 'Could not find IP.'


def ssh(env=DEFAULT_ENV_NAME):
    env = Environment(env)
    if env.ip:
        fabric.operations.local('ssh %s@%s' % (remote_user, env.ip))
    else:
        print 'Could not find IP.'


def destroy(env=DEFAULT_ENV_NAME):
    env = Environment(env)
    print 'Triggering environment deletion.'
    if env.server:
        env.server.delete()
        while env.server:
            time.sleep(1)
    else:
        print 'No environment exists.'
