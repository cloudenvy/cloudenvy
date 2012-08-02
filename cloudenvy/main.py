# vim: tabstop=4 shiftwidth=4 softtabstop=4

import argparse
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

from cloudenvy import cloud
from cloudenvy import exceptions
from cloudenvy import template


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
    'remote_user': 'ubuntu',
    'userdata': './userdata.sh',
}


def _get_config(args):
    global_config = os.environ.get('CLOUDENV_CONFIG',
                                   os.path.expanduser('~/.cloudenvy'))
    local_config = './.cloudenvy'
    configs = [global_config, local_config]

    logging.info('Loading config from: %s', configs)
    config = ConfigParser.ConfigParser(CONFIG_DEFAULTS)
    config.read(configs)

    logging.debug('Loaded config:')

    cloud_section = 'cloud:%s' % args.cloud
    logging.debug('[%s]', cloud_section)
    for opt in config.options(cloud_section):
        logging.debug('  %s = %s', opt, config.get(cloud_section, opt))

    template_section = 'template:%s' % args.template
    logging.debug('[%s]', template_section)
    for opt in config.options(template_section):
        logging.debug('  %s = %s', opt, config.get(template_section, opt))

    return config


def provision(args):
    """Manually provision a remote environment using a userdata script."""
    config = _get_config(args)
    env = template.Template(args.name, args, config)
    logging.info('Provisioning environment...')

    remote_user = args.remote_user or env.remote_user
    userdata_path = args.userdata or env.userdata
    logging.info('Using userdata from: %s', userdata_path)
    local_userdata_loc = args.userdata
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
    logging.info('...done.')


def up(args):
    """Create a server and show its IP."""
    env = template.Template(args.name, args, _get_config(args))
    if not env.server:
        logging.info('Building environment.')
        try:
            env.build_server()
        except exceptions.ImageNotFound:
            logging.error('Could not find image.')
            return
        except exceptions.NoIPsAvailable:
            logging.error('Could not find free IP.')
            return
    if env.ip:
        print env.ip
    else:
        print 'Environment has no IP.'


def snapshot(args, name=None):
    """Create a snapshot of a running server."""
    env = template.Template(args.name, args, _get_config(args))
    env.snapshot(name or ('%s-snapshot' % env.name))


def ip(args):
    """Show the IP of the current server."""
    env = template.Template(args.name, args, _get_config(args))

    if not env.server:
        logging.error('Environment has not been created.\n'
                      'Try running `envy up` first?')
    elif env.ip:
        print env.ip
    else:
        logging.error('Could not find IP.')


def ssh(args):
    """SSH into the current server."""
    env = template.Template(args.name, args, _get_config(args))
    if env.ip:
        remote_user = 'ubuntu'
        disable_known_hosts = ('-o UserKnownHostsFile=/dev/null'
                               ' -o StrictHostKeyChecking=no')
        fabric.operations.local('ssh %s %s@%s' % (disable_known_hosts,
                                                  remote_user,
                                                  env.ip))
    else:
        logging.error('Could not find IP.')


def destroy(args):
    """Power-off and destroy the current server."""
    env = template.Template(args.name, args, _get_config(args))
    logging.info('Triggering environment deletion.')
    if env.find_server():
        env.delete_server()
        while env.find_server():
            logging.info('...waiting for server to be destroyed')
            time.sleep(1)
        logging.info('...done.')
    else:
        logging.error('No environment exists.')


COMMANDS = [up, provision, snapshot, ip, ssh, destroy]


def main():
    parser = argparse.ArgumentParser(
            description='Launch a virtual machine in an openstack environment.')
    parser.add_argument('-v', '--verbosity', action='count',
                        help='increase output verbosity')
    parser.add_argument('-c', '--cloud', action='store',
                        help='specify which cloud to use',
                        default='envy')
    parser.add_argument('-t', '--template', action='store',
                        help='specify which instance template to use',
                        default='envy')
    parser.add_argument('-n', '--name', action='store',
                        help='specify a name for the instance',
                        default='envy')

    subparsers = parser.add_subparsers(title='Available commands:')

    for cmd in COMMANDS:
        cmd_name = cmd.func_name
        helptext = getattr(cmd, '__doc__', '')
        subparser = subparsers.add_parser(cmd_name, help=helptext)
        subparser.set_defaults(func=cmd)

        # NOTE(termie): add some specific options, if this ever gets too
        #               large we should probably switch to manually
        #               specifying each parser
        if cmd_name in ('provision', 'up'):
            subparser.add_argument('-u', '--userdata', action='store',
                                   help='specify the location of userdata',
                                   default=CONFIG_DEFAULTS['userdata'])
        if cmd_name in ('provision'):
            subparser.add_argument('-r', '--remote_user', action='store',
                                   help='remote user to provision',
                                   default=None)
        if cmd_name in ('up'):
            subparser.add_argument('-p', '--provision', action='store_true',
                                   help='supply userdata at server creation',
                                   default=False)

    args = parser.parse_args()

    if args.verbosity == 3:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('novaclient').setLevel(logging.DEBUG)
    elif args.verbosity == 2:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('novaclient').setLevel(logging.INFO)
    elif args.verbosity == 1:
        logging.getLogger().setLevel(logging.INFO)

    args.func(args)
