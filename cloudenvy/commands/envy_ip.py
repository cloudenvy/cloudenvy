import logging

from cloudenvy.envy import Envy


class EnvyIP(object):
    """Get the IP of an ENVy"""

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        subparser = subparsers.add_parser('ip', help='ip help')
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='specify custom name for an ENVy')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        if not envy.server():
            logging.error('ENVy is not running. Try running `envy up` first?')
        elif envy.ip():
            print envy.ip()
        else:
            logging.error('Could not find IP.')
