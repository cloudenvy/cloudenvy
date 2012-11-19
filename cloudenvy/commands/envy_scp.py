import logging

import fabric.api
import fabric.operations

from cloudenvy.envy import Envy


class EnvySCP(object):

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        help_str = 'Copy file(s) into your ENVy.'
        subparser = subparsers.add_parser('scp', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('source',
                help='Local path to copy into your ENVy.')
        subparser.add_argument('target',
                help='Location in your ENVy to place file(s). Non-absolute '
                     'paths are interpreted relative to remote_user homedir.')
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an ENVy.')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        if envy.ip():
            host_string = '%s@%s' % (envy.remote_user, envy.ip())

            with fabric.api.settings(host_string=host_string):
                fabric.operations.put(args.source, args.target)
        else:
            logging.error('Could not determine IP.')
