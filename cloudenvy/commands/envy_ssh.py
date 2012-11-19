import logging

import fabric.api
import fabric.operations

from cloudenvy.envy import Envy


class EnvySSH(object):

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        help_str = 'SSH into your ENVy.'
        subparser = subparsers.add_parser('ssh', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an ENVy.')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        if envy.ip():
            disable_known_hosts = ('-o UserKnownHostsFile=/dev/null'
                                   ' -o StrictHostKeyChecking=no')
            fabric.operations.local('ssh %s %s@%s' % (disable_known_hosts,
                                                      envy.remote_user,
                                                      envy.ip()))
        else:
            logging.error('Could not determine IP.')
