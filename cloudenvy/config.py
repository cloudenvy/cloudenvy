import getpass
import os
import os.path
import yaml

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


class EnvyConfig(object):
    """Base class for envy commands"""

    def __init__(self, args):
        self.args = args

    def get_config(self):
        args = self.args

        #NOTE(jakedahn): By popular request yml file extension is supported,
        #                but optional... for now.
        if os.path.isfile(os.path.expanduser('~/.cloudenvy')):
            user_config_path = os.path.expanduser('~/.cloudenvy')
        else:
            user_config_path = os.path.expanduser('~/.cloudenvy.yml')

        if os.path.isfile('./Envyfile'):
            project_config_path = './Envyfile'
        else:
            project_config_path = './Envyfile.yml'

        self._check_config_files(user_config_path, project_config_path)

        user_config = yaml.load(open(user_config_path))
        project_config = yaml.load(open(project_config_path))

        config = dict(CONFIG_DEFAULTS.items() + project_config.items()
                      + user_config.items())

        if 'name' in args:
            if args.name:
                config['project_config']['name'] = '%s-%s' % (
                    config['project_config']['name'], args.name)
        if 'userdata' in args:
            if args.userdata:
                config['project_config']['provision_script_path'] = \
                    args.userdata

        #TODO(jakedahn): I think this is stupid, there is probably a better way
        # Updae config dict with which cloud to use.
        if args.cloud:
            if args.cloud in config['cloudenvy']['clouds'].keys():
                config['cloudenvy'].update(
                    {'cloud': config['cloudenvy']['clouds'][args.cloud]})
        else:
            config['cloudenvy'].update(
                {'cloud': config['cloudenvy']['clouds'].itervalues().next()})

        self._validate_config(config)

        return config

    def _validate_config(self, config):
        for item in ['name', 'flavor_name', 'image_name']:
            config_item = config['project_config'].get(item)
            if config_item is None:
                raise SystemExit('Missing Configuration: Make sure `%s` is set'
                                 ' in your project\'s Envyfile' % item)

        if 'auto_provision' in config['project_config']:
            config_item = config['project_config'].get('provision_script_path')
            if config_item is None:
                raise SystemExit('Missing Configuration: Make sure `%s` is set'
                                 ' in your project\'s envy file')
        # If credentials config is not set, send output to user.
        for item in ['username', 'password', 'tenant_name', 'auth_url']:
            config_name = 'os_%s' % item
            config_item = config['cloudenvy']['cloud'].get(config_name)

            if config_item is None:
                raise SystemExit('Missing Credentials: Make sure `%s` is set '
                                 'in ~/.cloudenvy' % config_name)

    def _check_config_files(self, user_config_path, project_config_path):
        if not os.path.exists(user_config_path):
            raise SystemExit('Could not read ~/.cloudenvy. Please make sure '
                             '~/.cloudenvy has the proper configuration.')
        if not os.path.exists(project_config_path):
            raise SystemExit('Could not read ./Envyfile. Please make sure you'
                             'have an EnvyFile in your current directory.')
