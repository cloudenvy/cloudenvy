import logging

from cloudenvy import exceptions
from cloudenvy.commands.envy_provision import EnvyProvision
from cloudenvy.envy import Envy


class EnvyUp(object):
    """Create a cloud ENVy (development environment in the cloud!)"""

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        subparser = subparsers.add_parser('up', help='up help')
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='specify custom name for an ENVy')
        subparser.add_argument('-c', '--cloud', action='store', default='',
                               help='specify which cloud to use')
        subparser.add_argument('-u', '--userdata', action='store',
                               help='specify the location of userdata')
        subparser.add_argument('-p', '--provision', action='store_true',
                               help='supply userdata at server creation',
                               default=False)
        subparser.add_argument('--manual-provision', action='store_true',
                               help='Override `auto_provision` setting in '
                               'your Envyfile to not auto provision')
        subparser.add_argument('--auto-provision', action='store_true',
                               help='Override `auto_provision` setting in '
                               'your Envyfile to auto provision')
        return subparser

    def run(self, config, args):
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
            EnvyProvision().run(config, args)
        if envy.ip():
            print envy.ip()
        else:
            print 'Environment has no IP.'
