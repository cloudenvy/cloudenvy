# vim: tabstop=4 shiftwidth=4 softtabstop=4

import argparse
import getpass
import logging
import os
import os.path
import tarfile
import tempfile
import time
import yaml

import fabric.api
import fabric.operations

from cloudenvy import exceptions
from cloudenvy.envy import Envy


CONFIG_DEFAULTS = {
    'defaults': {
        'keypair_name': getpass.getuser(),
        'keypair_location': os.path.expanduser('~/.ssh/id_rsa.pub'),
        'flavor_name': 'm1.small',
        'sec_group_name': 'cloudenvy',
        'remote_user': 'ubuntu',
        'auto_provision': False,
        'dotfiles': '.vimrc, .gitconfig, .gitignore, .screenrc',
        'sec_groups': [
            'icmp, -1, -1, 0.0.0.0/0',
            'tcp, 22, 22, 0.0.0.0/0',
            'tcp, 443, 443, 0.0.0.0/0',
            'tcp, 80, 80, 0.0.0.0/0',
            'tcp, 8080, 8080, 0.0.0.0/0',
            'tcp, 5000, 5000, 0.0.0.0/0',
            'tcp, 9292, 9292, 0.0.0.0/0'
        ]
    }
}


def _validate_config(config):
    for item in ['name', 'flavor_name', 'image_name']:
        config_item = config['project_config'].get(item)
        if config_item is None:
            raise SystemExit('Missing Configuration: Make sure `%s` is set in '
                             'your project\'s Envyfile' % item)

    if 'auto_provision' in config['project_config']:
        config_item = config['project_config'].get('provision_script_path')
        if config_item is None:
            raise SystemExit('Missing Configuration: Make sure `%s` is set in '
                             'your project\'s envy file')
    # If credentials config is not set, send output to user.
    for item in ['username', 'password', 'tenant_name', 'auth_url']:
        config_name = 'os_%s' % item
        config_item = config['cloudenvy']['cloud'].get(config_name)

        if config_item is None:
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

    user_config = yaml.load(open(user_config_path))
    project_config = yaml.load(open(project_config_path))

    config = dict(CONFIG_DEFAULTS.items() + project_config.items()
                  + user_config.items())

    # Updae config dict with which cloud to use.
    if args.cloud:
        if args.cloud in config['cloudenvy']['clouds'].keys():
            config['cloudenvy'].update(
                {'cloud': config['cloudenvy']['clouds'][args.cloud]})
    else:
        config['cloudenvy'].update(
            {'cloud': config['cloudenvy']['clouds'].itervalues().next()})
    # Exits if there are issues with configuration.
    _validate_config(config)

    return config


def envy_list(args):
    """List all ENVys in context of your current project"""
    config = _get_config(args)
    envy = Envy(config)
    foo = envy.list_servers()

    envys = []
    for server in foo:
        if len(server.name.split(envy.name)) > 1:
            envys.append(str(server.name))
    print "ENVys for your project: %s" % str(envys)


def envy_up(args):
    """Create a server and show its IP."""
    config = _get_config(args)

    # if user defines -n in cli, append name to project name.
    if args.name:
        config['project_config']['name'] = '%s-%s' % (
            config['project_config']['name'], args.name)

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
    if envy.auto_provision and not args.manual_provision:
        envy_provision(args)
    if envy.ip():
        print envy.ip()
    else:
        print 'Environment has no IP.'


def envy_provision(args):
    """Manually provision a remote environment using a userdata script."""
    config = _get_config(args)

    # if user defines -n in cli, append name to project name.
    if args.name:
        config['project_config']['name'] = '%s-%s' % (
            config['project_config']['name'], args.name)
    if args.userdata:
        config['project_config']['provision_script_path'] = args.userdata

    envy = Envy(config)
    logging.info('Provisioning %s environment...' %
                 envy.project_config['name'])

    try:
        provision_script_path = envy.project_config['provision_script_path']
    except KeyError:
        raise SystemExit('Please specify which provision script should be used'
                         ' by passing in `-u` to the provision command, or by '
                         'defining `provision_script_path` in ./Envyfile')
    remote_provision_script_path = '~/provision_script'

    logging.info('Using userdata from: %s', provision_script_path)

    with fabric.api.settings(host_string=envy.ip(),
                             user=envy.remote_user,
                             forward_agent=True,
                             disable_known_hosts=True):
        for i in range(12):
            try:
                fabric.operations.run('if [ -e "$HOME/provision_script" ]; '
                                      'then rm ~/provision_script; fi')
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


def envy_snapshot(args, name=None):
    """Create a snapshot of a running server."""
    config = _get_config(args)

    # if user defines -n in cli, append name to project name.
    if args.name:
        config['project_config']['name'] = '%s-%s' % (
            config['project_config']['name'], args.name)

    envy = Envy(config)
    envy.snapshot(name or ('%s-snapshot' % envy.name))


def envy_ip(args):
    """Show the IP of the current server."""
    config = _get_config(args)

     # if user defines -n in cli, append name to project name.
    if args.name:
        config['project_config']['name'] = '%s-%s' % (
            config['project_config']['name'], args.name)

    envy = Envy(config)

    if not envy.server():
        logging.error('Environment has not been created.\n'
                      'Try running `envy up` first?')
    elif envy.ip():
        print envy.ip()
    else:
        logging.error('Could not find IP.')


def envy_scp(args):
    """SCP Files to your ENVy"""
    config = _get_config(args)

    # if user defines -n in cli, append name to project name.
    if args.name:
        config['project_config']['name'] = '%s-%s' % (
            config['project_config']['name'], args.name)

    envy = Envy(config)

    if envy.ip():
        remote_user = 'ubuntu'
        host_string = '%s@%s' % (remote_user, envy.ip())

        with fabric.api.settings(host_string=host_string):
            fabric.operations.put(args.source, args.target)
    else:
        logging.error('Could not find IP to upload file to.')


def envy_dotfiles(args):
    """Upload user dotfiles from local machine."""
    config = _get_config(args)

    # if user defines -n in cli, append name to project name.

    if args.name:
        config['project_config']['name'] = '%s-%s' % (
            config['project_config']['name'], args.name)

    envy = Envy(config)

    if envy.ip():
        host_string = '%s@%s' % (envy.remote_user, envy.ip())

        temp_tar = tempfile.NamedTemporaryFile(delete=True)

        with fabric.api.settings(host_string=host_string):
            if args.files:
                dotfiles = args.files.split(', ')
            else:
                dotfiles = config['defaults']['dotfiles'].split(', ')

            with tarfile.open(temp_tar.name, 'w') as archive:
                for dotfile in dotfiles:
                    path = os.path.expanduser('~/%s' % dotfile)
                    if os.path.exists(path):
                        if not os.path.islink(path):
                            archive.add(path, arcname=dotfile)

            fabric.operations.put(temp_tar, '~/dotfiles.tar')
            fabric.operations.run('tar -xvf ~/dotfiles.tar')
    else:
        logging.error('Could not find IP to upload file to.')


def envy_ssh(args):
    """SSH into the current server."""
    config = _get_config(args)

    # if user defines -n in cli, append name to project name.
    if args.name:
        config['project_config']['name'] = '%s-%s' % (
            config['project_config']['name'], args.name)

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


def envy_destroy(args):
    """Power-off and destroy the current server."""
    config = _get_config(args)

    # if user defines -n in cli, append name to project name.
    if args.name:
        config['project_config']['name'] = '%s-%s' % (
            config['project_config']['name'], args.name)

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


COMMANDS = [envy_up, envy_provision, envy_snapshot, envy_ip, envy_ssh,
            envy_destroy, envy_scp, envy_list, envy_dotfiles]


def _build_parser():
    parser = argparse.ArgumentParser(
        description='Launch a virtual machine in an openstack environment.')
    parser.add_argument('-v', '--verbosity', action='count',
                        help='increase output verbosity')
    parser.add_argument('-c', '--cloud', action='store',
                        help='specify which cloud to use')

    subparsers = parser.add_subparsers(title='Available commands:')

    for cmd in COMMANDS:
        cmd_name = cmd.func_name.split('envy_')[1]
        helptext = getattr(cmd, '__doc__', '')
        subparser = subparsers.add_parser(cmd_name, help=helptext)
        subparser.set_defaults(func=cmd)

        # NOTE(termie): add some specific options, if this ever gets too
        #               large we should probably switch to manually
        #               specifying each parser
        if cmd_name in ('up', 'provision', 'snapshot', 'ip', 'scp', 'ssh',
                        'destroy', 'dotfiles'):
            subparser.add_argument('-n', '--name', action='store', default='',
                                   help='specify custom name for an ENVy')
            subparser.add_argument('-c', '--cloud', action='store', default='',
                                   help='specify which cloud to use')

        if cmd_name in ('provision', 'up'):
            subparser.add_argument('-u', '--userdata', action='store',
                                   help='specify the location of userdata')

        if cmd_name in ('up'):
            subparser.add_argument('-p', '--provision', action='store_true',
                                   help='supply userdata at server creation',
                                   default=False)
            subparser.add_argument('--manual-provision', action='store_true',
                                   help='Override `auto_provision` setting in '
                                   'your Envyfile to not auto provision')
            subparser.add_argument('--auto-provision', action='store_true',
                                   help='Override `auto_provision` setting in '
                                   'your Envyfile to auto provision')
        if cmd_name in ('scp'):
            subparser.add_argument('source')
            subparser.add_argument('target')

        if cmd_name in ('dotfiles'):
            subparser.add_argument('-f', '--files', action='store',
                                   help='define which dotfiles to upload '
                                        '(comma space separated)')
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
