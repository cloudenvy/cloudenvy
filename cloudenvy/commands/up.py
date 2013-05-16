import logging

from cloudenvy import exceptions
import cloudenvy.envy


class Up(cloudenvy.envy.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Create and optionally provision an ENVy.'
        subparser = subparsers.add_parser('up', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an ENVy.')
        subparser.add_argument('-s', '--scripts', nargs='*', metavar='PATH',
                               default=None,
                               help='Override provision_script_paths option '
                                    'in project config.')
        subparser.add_argument('--no-files', action='store_true',
                               help='Prevent files from being uploaded')
        subparser.add_argument('--no-provision', action='store_true',
                               help='Prevent provision scripts from running.')
        return subparser

    def run(self, config, args):
        envy = cloudenvy.envy.Envy(config)

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
        if not args.no_files:
            self.commands['files'].run(config, args)
        if not args.no_provision \
                and (envy.project_config.get("auto_provision", True) \
                and 'provision_scripts' in envy.project_config):
            try:
                self.commands['provision'].run(config, args)
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
