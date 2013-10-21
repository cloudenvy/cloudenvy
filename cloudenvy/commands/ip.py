import logging

import cloudenvy.core


class Ip(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Print IPv4 address of Envy.'
        subparser = subparsers.add_parser('ip', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if not envy.server():
            logging.error('Envy is not running.')
        elif envy.ip():
            print envy.ip()
        else:
            logging.error('Could not determine IP.')
