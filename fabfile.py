import os
import os.path
import time

import fabric.api
import novaclient.exceptions
import novaclient.client


fabric.api.env.user = os.environ.get('CE_USER', 'ubuntu')
fabric.api.env.hosts = [os.environ.get('CE_HOST')]
DEFAULT_ENV_NAME = 'cloudenvy'
userdata_location = os.environ.get('CE_USERDATA_LOCATION', './userdata')
sec_group_name = os.environ.get('CE_SEC_GROUP_NAME', 'cloudenvy')
keypair_name = os.environ.get('CE_KEY_NAME', 'cloudenvy')
pubkey_location = os.environ.get('CE_KEY_LOCATION',
                                 os.path.expanduser('~/.ssh/id_rsa.pub'))




class FixedIPAssignFailure(RuntimeError):
    pass


class NoFloatingIPsAvailable(RuntimeError):
    pass


def _get_nova_client():
    """create a new nova client"""
    user = os.environ.get('OS_USERNAME')
    password = os.environ.get('OS_PASSWORD')
    tenant = os.environ.get('OS_TENANT_NAME')
    auth_url = os.environ.get('OS_AUTH_URL')
    return novaclient.client.Client('2', user, password, tenant, auth_url,
                                    service_type='compute')


def _get_floating_ip(client, server):
    fips = client.floating_ips.list()

    # Iterate once to check for existing assignment
    for fip in fips:
        if fip.instance_id == server.id:
            return fip

    # Now try to assign an IP
    for fip in fips:
        if not fip.instance_id:
            server.add_floating_ip(fip.ip)
            return fip

    raise NoFloatingIPsAvailable()


def _ensure_keypair_exists(client):
    try:
        client.keypairs.find(name=keypair_name)
    except novaclient.exceptions.NotFound:
        fap = open(pubkey_location, 'r')
        data = fap.read()
        fap.close()
        client.keypairs.create(keypair_name, public_key=data)


def _ensure_sec_group_exists(client):
    try:
        sec_group = client.security_groups.find(name=sec_group_name)
    except novaclient.exceptions.NotFound:
        sec_group = client.security_groups.create(sec_group_name,
                                                  sec_group_name)
        pg_id = sec_group.id
        client.security_group_rules.create(pg_id,
                'icmp', -1, -1, '0.0.0.0/0')
        client.security_group_rules.create(pg_id,
                'tcp', 22, 22, '0.0.0.0/0')
        client.security_group_rules.create(pg_id,
                'tcp', 8080, 8080, '0.0.0.0/0')


def _find_server(client, env_name):
    try:
        return client.servers.find(name=env_name)
    except novaclient.exceptions.NotFound:
        return None


def _read_userdata():
    fap = open(userdata_location, 'r')
    data = fap.read()
    fap.close()
    return data


def _get_server(client, env_name):
    server = _find_server(client, env_name)
    if not server:
        image_name = os.environ.get('CE_IMAGE_NAME',
                                    'precise-server-cloudimg-amd64')
        image = client.images.find(name=image_name)
        flavor_name = os.environ.get('CE_FLAVOR_NAME', 'm1.large')
        flavor = client.flavors.find(name=flavor_name)

        _ensure_sec_group_exists(client)
        _ensure_keypair_exists(client)

        server = client.servers.create(env_name,
                                       image,
                                       flavor,
                                       userdata=_read_userdata(),
                                       key_name=keypair_name,
                                       security_groups=[sec_group_name])

        # Wait for server to get fixed ip
        for i in xrange(60):
            server = client.servers.get(server.id)
            if len(server.networks):
                return server
            if i == 59:
                raise FixedIPAssignFailure()

    return server


def up(name=DEFAULT_ENV_NAME):
    """create the cloud environment if it doesn't exist"""
    client = _get_nova_client()
    server = _get_server(client, name)
    fip = _get_floating_ip(client, server)
    print 'Environment IP: %s' % fip.ip


def destroy(name=DEFAULT_ENV_NAME):
    """Destroy an existing server"""
    client = _get_nova_client()
    server = _find_server(client, name)
    if server:
        server.delete()
        print "Triggering environment deletion."
        while _find_server(client, name):
            time.sleep(1)
    else:
        print "No environment found."
