import getpass
import logging
import os
import sys
import os.path
import yaml

CONFIG_DEFAULTS = {
    'defaults': {
        'keypair_name': getpass.getuser(),
        'keypair_location': os.path.expanduser('~/.ssh/id_rsa.pub'),
        'flavor_name': 'm1.small',
        'remote_user': 'ubuntu',
        'auto_provision': False,
        'forward_agent': True,
        'dotfiles': '.vimrc, .gitconfig, .gitignore, .screenrc',
        'sec_groups': [
            'icmp, -1, -1, 0.0.0.0/0',
            'tcp, 22, 22, 0.0.0.0/0',
        ]
    }
}


class EnvyConfig(object):
    """Base class for envy commands"""

    def __init__(self, args):
        self.args = args
        self.config = None

    def __getitem__(self, item):
        if not self.config:
            self.config = self.get_config()
        return self.config[item]

    def __setitem__(self, item, value):
        if not self.config:
            self.config = self.get_config()
        self.config[item] = value

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

        base_name = config['project_config']['name']
        try:
            envy_name = args.name
            assert envy_name
        except (AssertionError, AttributeError):
            pass
        else:
            config['project_config']['name'] = '%s-%s' % (base_name, envy_name)
        finally:
            config['project_config']['base_name'] = base_name

        if 'keypair_location' in config['cloudenvy']:
            full_path = os.path.expanduser(
                                config['cloudenvy']['keypair_location'])
            config['cloudenvy']['keypair_location'] = full_path

        #TODO(jakedahn): I think this is stupid, there is probably a better way
        # Updae config dict with which cloud to use.
        if args.cloud:
            if args.cloud in config['cloudenvy']['clouds'].keys():
                config['cloudenvy'].update(
                    {'cloud': config['cloudenvy']['clouds'][args.cloud]})
            else:
                logging.error("Cloud %s is not found in your config" % args.cloud)
                logging.debug("Clouds Found %s" % ", ".join(config['cloudenvy']['clouds'].keys()))
                sys.exit(1)
        else:
            config['cloudenvy'].update(
                {'cloud': config['cloudenvy']['clouds'].itervalues().next()})

        self._validate_config(config, user_config_path, project_config_path)

        return config

    def _validate_config(self, config, user_config_path, project_config_path):
        if 'image_name' in config['project_config']:
            logging.warning('Please note that using `image_name` option in your '
                          'Envyfile has been deprecated. Please use the '
                          '`image` option instead. `image_name` will no '
                          'longer be supported as of December 01, 2012.')
        if 'image_id' in config['project_config']:
            logging.warning('Please note that using `image_id` option in your '
                          'Envyfile has been deprecated. Please use the '
                          '`image` option instead. `image_id` will no '
                          'longer be supported as of December 01, 2012.')

        for item in ['name']:
            config_item = config['project_config'].get(item)
            if config_item is None:
                raise SystemExit('Missing Configuration: Make sure `%s` is set'
                                 ' in %s' % (item, project_config_path))

        # If credentials config is not set, send output to user.
        for item in ['username', 'password', 'tenant_name', 'auth_url']:
            config_name = 'os_%s' % item
            config_item = config['cloudenvy']['cloud'].get(config_name)

            if config_item is None:
                raise SystemExit('Missing Credentials: Make sure `%s` is set '
                                 'in %s' % (config_name, user_config_path))

    def _check_config_files(self, user_config_path, project_config_path):
        if not os.path.exists(user_config_path):
            raise SystemExit('Could not read `%s`. Make sure '
                             '~/.cloudenvy has the proper configuration.'
                             % user_config_path)
        if not os.path.exists(project_config_path):
            raise SystemExit('Could not read `%s`. Make sure you '
                             'have an EnvyFile in your current directory.'
                             % project_config_path)
