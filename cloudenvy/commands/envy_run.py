import logging

import fabric.api
import fabric.operations

from cloudenvy.envy import Envy


class EnvyRun(object):

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        help_str = 'Execute a command in your ENVy.'
        subparser = subparsers.add_parser('run', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('command', help='Command to execute remotely.')
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an ENVy.')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        if envy.ip():
            host_string = '%s@%s' % (envy.remote_user, envy.ip())
            with fabric.api.settings(host_string=host_string):
                fabric.operations.run(args.command)
        else:
            logging.error('Could not determine IP.')
