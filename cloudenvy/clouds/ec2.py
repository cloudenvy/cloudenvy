import collections
import time
import urlparse

import boto.ec2.connection


Server = collections.namedtuple('Server', ['id', 'name'])
Image = collections.namedtuple('Image', ['id', 'name'])


class CloudAPI(object):
    def __init__(self, config):
        self._client = None
        self.config = config

        ec2_endpoint = self.config.user_config['cloud'].get('ec2_endpoint', None)
        self.endpoint = urlparse.urlparse(ec2_endpoint)
        self.access_key = self.config.user_config['cloud'].get('ec2_access_key', None)
        self.secret_key = self.config.user_config['cloud'].get('ec2_secret_key', None)
        self.region_name = self.config.user_config['cloud'].get('ec2_region_name', 'RegionOne')

    @property
    def client(self):
        if not self._client:
            region = boto.ec2.regioninfo.RegionInfo(
                    name=self.region_name, endpoint=self.endpoint.hostname)

            kwargs = {
                'aws_access_key_id': self.access_key,
                'aws_secret_access_key': self.secret_key,
                'is_secure': self.endpoint.scheme == 'https',
                'host': self.endpoint.hostname,
                #'port': self.endpoint.port,
                'path': self.endpoint.path,
                'validate_certs': False,
                'region': region,
            }
            self._client = boto.ec2.connection.EC2Connection(**kwargs)
        return self._client

    @staticmethod
    def _instance_to_dict(instance):
        return Server(id=instance.id, name=instance.tags.get('Name', ''))

    @staticmethod
    def _image_to_dict(image):
        return Image(id=image.id, name=image.id)

    def is_server_active(self, server_id):
        inst = self._get_server(server_id)
        return inst.state == 'running'

    def is_network_active(self, server_id):
        inst = self._get_server(server_id)
        return bool(inst.ip_address)

    def list_servers(self):
        instances = self.client.get_only_instances(filters={'instance-state-name': 'running'})
        return [self._instance_to_dict(inst) for inst in instances]

    def find_server(self, name):
        servers = self.list_servers()
        for server in servers:
            if server.name == name:
                return server

    def _get_server(self, server_id):
        instances = self.client.get_only_instances([server_id])
        return instances[0] if instances else None

    def get_server(self, server_id):
        inst = self._get_server(server_id)
        return self._instance_to_dict(inst) if inst else None

    def create_server(self, *args, **kwargs):
        name = kwargs.pop('name')
        image = kwargs.pop('image')
        flavor = kwargs.pop('flavor')
        meta = kwargs.pop('meta', {})
        security_groups = kwargs.pop('security_groups')
        key_name = kwargs.pop('key_name')

        _kwargs = {
            'key_name': key_name,
            'security_groups': security_groups,
            'instance_type': flavor,
        }

        image = self._find_image(image.id)
        reservation = image.run(**_kwargs)
        instance = reservation.instances[0]
        status = instance.update()

        for i in xrange(60):
            status = instance.update()
            if status == 'running':
                break
            time.sleep(1)
        else:
            raise

        instance.add_tag('Name', name)

        return self._instance_to_dict(instance)

    def setup_network(self, server_id):
        #NOTE(bcwaldon): We depend on EC2 to do this for us today
        return

    def find_ip(self, server_id):
        instance = self._get_server(server_id)
        return instance.ip_address

    def _find_image(self, image_id):
        #NOTE(bcwaldon): This only works with image ids for now
        return self.client.get_image(image_id)

    def find_image(self, search_str):
        image = self._find_image(search_str)
        return self._image_to_dict(image)

    def snapshot(self, server, name):
        raise NotImplementedError()

    def find_flavor(self, name):
        return name

    def _find_security_group(self, name):
        try:
            return self.client.get_all_security_groups([name])[0]
        except boto.exception.EC2ResponseError:
            return None

    def find_security_group(self, name):
        sg = self._find_security_group(name)
        return name if sg else None

    def create_security_group(self, name):
        self.client.create_security_group(name, name)
        return name

    def create_security_group_rule(self, name, rule):
        sg = self._find_security_group(name)
        if not sg:
            raise

        try:
            sg.authorize(*rule)
        except boto.exception.EC2ResponseError:
            pass

    def find_keypair(self, name):
        return self.client.get_key_pair(name)

    def create_keypair(self, name, key_data):
        self.client.import_key_pair(name, key_data)

    def delete_server(self, server):
        self.client.terminate_instances([server.id])
