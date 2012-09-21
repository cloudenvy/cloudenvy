# vim: tabstop=4 shiftwidth=4 softtabstop=4

import argparse
import logging
import os
import os.path
import time
import yaml

import fabric.api
import fabric.operations

from cloudenvy import exceptions
from cloudenvy.envy import Envy


CONFIG_DEFAULTS = {
    'keypair_name': os.getlogin(),
    'keypair_location': os.path.expanduser('~/.ssh/id_rsa.pub'),
    'flavor_name': 'm1.small',
    'sec_group_name': 'cloudenvy',
    'remote_user': 'ubuntu',
    'auto_provision': False,
}


def _validate_config(config):
    for item in ['name', 'flavor_name']:
        config_item = config['project_config'].get(item)
        if config_item == None:
            raise SystemExit('Missing Configuration: Make sure `%s` is set in '
                             'your project\'s Envyfile')

    # If credentials config is not set, send output to user.
    for item in ['username', 'password', 'tenant_name', 'auth_url']:
        config_name = 'os_%s' % item
        config_item = config['cloudenvy']['cloud'].get(config_name)

        if config_item == None:
            raise SystemExit('Missing Credentials: Make sure `%s` is set in '
                             '~/.cloudenvy' % config_name)


def _check_config_files(user_config_path, project_config_path):
    if not os.path.exists(user_config_path):
        raise SystemExit('Could not read ~/.cloudenvy. Please make sure '
                         '~/.cloudenvy has the proper configuration.')

    if not os.path.exists(project_config_path):
        raise SystemExit('Could not read ./Envyfile. Please make sure you'
                         'have an EnvyFile in your current directory.')


#TODO(jakedahn): clean up this entire method, it's kind of hacky.
def _get_config(args):
    user_config_path = os.path.expanduser('~/.cloudenvy')
    project_config_path = './Envyfile'

    _check_config_files(user_config_path, project_config_path)

    user_config = {'cloudenvy': CONFIG_DEFAULTS}
    user_yaml = yaml.load(open(user_config_path))['cloudenvy']
    user_config.update({'cloudenvy': user_yaml})
    project_config = yaml.load(open(project_config_path))

    config = dict(project_config.items() + user_config.items())

    # Updae config dict with which cloud to use.
    if args.cloud:
        if args.cloud in config['cloudenvy']['clouds'].keys():
            config['cloudenvy'].update(
                {'cloud': ['cloudenvy']['clouds'][args.cloud]})
    else:
        config['cloudenvy'].update(
            {'cloud': config['cloudenvy']['clouds'].itervalues().next()})
    # Exits if there are issues with configuration.
    _validate_config(config)
    return config


def up(args):
    """Create a server and show its IP."""
    config = _get_config(args)
    envy = Envy(config)
    if not envy.server():
        logging.info('Building environment.')
        try:
            envy.build_server()
        except exceptions.ImageNotFound:
            logging.error('Could not find image.')
            return
        except exceptions.NoIPsAvailable:
            logging.error('Could not find free IP.')
            return
    if envy.auto_provision:
        provision(args)
    if envy.ip():
        print envy.ip()
    else:
        print 'Environment has no IP.'


def provision(args):
    """Manually provision a remote environment using a userdata script."""
    config = _get_config(args)
    envy = Envy(config)
    logging.info('Provisioning %s environment...' %
                 config['project_config']['name'])

    remote_user = config['project_config']['remote_user']
    provision_script_path = config['project_config']['provision_script_path']
    remote_provision_script_path = '~/provision_script'

    logging.info('Using userdata from: %s', provision_script_path)

    with fabric.api.settings(host_string=envy.ip(),
                             user=remote_user,
                             forward_agent=True,
                             disable_known_hosts=True):
        for i in range(12):
            try:
                fabric.operations.put(provision_script_path,
                                      remote_provision_script_path,
                                      mode=0755)
                break
            except fabric.exceptions.NetworkError:
                logging.error("Unable to upload file. Your cloud instance is "
                              "probably not yet built. Trying again in 10 "
                              "seconds.")
                time.sleep(10)

        fabric.operations.run(remote_provision_script_path)
    logging.info('...done.')


def snapshot(args, name=None):
    """Create a snapshot of a running server."""
    config = _get_config(args)
    envy = Envy(config)
    envy.snapshot(name or ('%s-snapshot' % envy.name))


def ip(args):
    """Show the IP of the current server."""
    config = _get_config(args)
    envy = Envy(config)

    if not envy.server():
        logging.error('Environment has not been created.\n'
                      'Try running `envy up` first?')
    elif envy.ip():
        print envy.ip()
    else:
        logging.error('Could not find IP.')


def scp(args):
    """SCP Files to your ENVy"""
    config = _get_config(args)
    envy = Envy(config)

    if envy.ip():
        remote_user = 'ubuntu'
        host_string = '%s@%s' % (remote_user, envy.ip())

        with fabric.api.settings(host_string=host_string):
            fabric.operations.put(args.source, args.target)
    else:
        logging.error('Could not find IP to upload file to.')


def ssh(args):
    """SSH into the current server."""
    config = _get_config(args)
    envy = Envy(config)
    remote_user = config['project_config']['remote_user']
    if envy.ip():
        disable_known_hosts = ('-o UserKnownHostsFile=/dev/null'
                               ' -o StrictHostKeyChecking=no')
        fabric.operations.local('ssh %s %s@%s' % (disable_known_hosts,
                                                  remote_user,
                                                  envy.ip()))
    else:
        logging.error('Could not find IP.')


def destroy(args):
    """Power-off and destroy the current server."""
    config = _get_config(args)
    envy = Envy(config)
    logging.info('Triggering environment deletion.')
    if envy.find_server():
        envy.delete_server()
        while envy.find_server():
            logging.info('...waiting for server to be destroyed')
            time.sleep(1)
        logging.info('...done.')
    else:
        logging.error('No environment exists.')


COMMANDS = [up, provision, snapshot, ip, ssh, destroy, scp]


def _build_parser():
    parser = argparse.ArgumentParser(
        description='Launch a virtual machine in an openstack environment.')
    parser.add_argument('-v', '--verbosity', action='count',
                        help='increase output verbosity')
    parser.add_argument('-c', '--cloud', action='store',
                        help='specify which cloud to use')

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
                                   help='specify the location of userdata')
        if cmd_name in ('provision'):
            subparser.add_argument('-r', '--remote_user', action='store',
                                   help='remote user to provision',
                                   default=None)
        if cmd_name in ('up'):
            subparser.add_argument('-p', '--provision', action='store_true',
                                   help='supply userdata at server creation',
                                   default=False)
        if cmd_name in ('scp'):
            subparser.add_argument('source')
            subparser.add_argument('target')

    return parser


def main():
    parser = _build_parser()
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
