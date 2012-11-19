import logging

from cloudenvy.envy import Envy


class EnvyIP(object):

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        help_str = 'Print IPv4 address of ENVy.'
        subparser = subparsers.add_parser('ip', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an ENVy.')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        if not envy.server():
            logging.error('ENVy is not running.')
        elif envy.ip():
            print envy.ip()
        else:
            logging.error('Could not determine IP.')
