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
        'default_cloud': None,
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

    def _set_working_cloud(self, cloud_name, config):
        """Sets which cloud to operate on based on config values and parameters
        """
        try:
            known_clouds = config['cloudenvy']['clouds'].keys()
        except (KeyError, AttributeError):
            logging.error('No clouds defined in config file')
            sys.exit(1)

        if cloud_name in known_clouds:
            config['cloudenvy'].update(
                {'cloud': config['cloudenvy']['clouds'][cloud_name]})
        else:
            logging.error("Cloud %s is not found in your config" % cloud_name)
            logging.debug("Clouds Found %s" % ", ".join(
                          config['cloudenvy']['clouds'].keys()))
            sys.exit(1)

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

        #TODO(jakedahn): I think this is stupid, there is probably a better way
        # Update config dict with which cloud to use.
        if args.cloud:
            # If a specific cloud is requested, use it.
            self._set_working_cloud(args.cloud, config)
        elif config['cloudenvy'].get('default_cloud'):
            # If no specific cloud is requested, try the default.
            cloud_name = config['cloudenvy']['default_cloud']
            self._set_working_cloud(cloud_name, config)
        else:
            try:
                num_clouds = len(config['cloudenvy']['clouds'].keys())
            except (KeyError, TypeError, AttributeError):
                logging.error('Unable to parse clouds from config file')
                sys.exit(1)

            if num_clouds == 0:
                logging.error('No clouds defined in config file')
                sys.exit(1)
            elif num_clouds > 1:
                logging.error('Define default_cloud in your cloudenvy config '
                              'or specify the --cloud flag')
                sys.exit(1)

            # No explicit cloud defined, but there's only one so we can
            # safely default to that.
            cloud_name = config['cloudenvy']['clouds'].keys()[0]
            self._set_working_cloud(cloud_name, config)

        self._validate_config(config, user_config_path, project_config_path)

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

        return config

    def _validate_config(self, config, user_config_path, project_config_path):
        if 'image_name' in config['project_config']:
            logging.warning('Please note that using `image_name` option in '
                          'your Envyfile has been deprecated. Please use the '
                          '`image` option instead. `image_name` will no '
                          'longer be supported as of December 01, 2012.')
        if 'image_id' in config['project_config']:
            logging.warning('Please note that using `image_id` option in your '
                          'Envyfile has been deprecated. Please use the '
                          '`image` option instead. `image_id` will no '
                          'longer be supported as of December 01, 2012.')

        try:
            config['project_config']['name']
        except KeyError:
            raise SystemExit("Ensure 'name' is set in %s"
                             % project_config_path)

        for item in ['os_username', 'os_tenant_name', 'os_auth_url']:
            try:
                config['cloudenvy']['cloud'][item]
            except KeyError:
                raise SystemExit("Ensure '%s' is set in %s"
                                 % (item, user_config_path))

        try:
            password = config['cloudenvy']['cloud']['os_password']
        except KeyError:
            username = config['cloudenvy']['cloud']['os_username']
            prompt = "Password for account '%s': " % username
            password = getpass.getpass(prompt)
            config['cloudenvy']['cloud']['os_password'] = password

    def _check_config_files(self, user_config_path, project_config_path):
        if not os.path.exists(user_config_path):
            raise SystemExit('Could not read `%s`. Make sure '
                             '~/.cloudenvy has the proper configuration.'
                             % user_config_path)
        if not os.path.exists(project_config_path):
            raise SystemExit('Could not read `%s`. Make sure you '
                             'have an EnvyFile in your current directory.'
                             % project_config_path)
