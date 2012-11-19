import logging

from cloudenvy import exceptions
from cloudenvy.commands.envy_provision import EnvyProvision
from cloudenvy.envy import Envy


class EnvyUp(object):

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        help_str = 'Create and optionally provision an ENVy.'
        subparser = subparsers.add_parser('up', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an ENVy.')
        subparser.add_argument('-s', '--scripts', default=None, nargs='*',
                               help='Override provision_script_paths option '
                                    'in project config.')
        subparser.add_argument('--no-provision', action='store_true',
                               help='Prevent provision scripts from running.')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        if not envy.server():
            logging.info('Triggering ENVy boot.')
            try:
                envy.build_server()
            except exceptions.ImageNotFound:
                logging.error('Could not find image.')
                return
            except exceptions.NoIPsAvailable:
                logging.error('Could not find available IP.')
                return
        if not args.no_provision and 'provision_scripts' in envy.project_config:
            try:
                EnvyProvision().run(config, args)
            except SystemExit:
                raise SystemExit('You have not specified any provision '
                                 'scripts in your Envyfile. '
                                 'If you would like to run your ENVy '
                                 'without a provision script; use the '
                                 '`--no-provision` command line flag.')
        if envy.ip():
            print envy.ip()
        else:
            logging.error('Could not determine IP.')
