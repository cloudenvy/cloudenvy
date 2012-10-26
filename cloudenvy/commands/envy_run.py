import logging

import fabric.api
import fabric.operations

from cloudenvy.envy import Envy


class EnvyRun(object):
    """Run commands on your ENVy"""

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        subparser = subparsers.add_parser('run', help='run help')
        subparser.set_defaults(func=self.run)

        subparser.add_argument('command')
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='specify custom name for an ENVy')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        if envy.ip():
            host_string = '%s@%s' % (envy.remote_user, envy.ip())
            with fabric.api.settings(host_string=host_string):
                fabric.operations.run(args.command)
        else:
            logging.error('Unable to run command on ENVy, perhaps its not '
                          'booted yet?.')
