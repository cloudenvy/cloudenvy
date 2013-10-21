import logging

import fabric.api
import fabric.operations
import os

import cloudenvy.core


class Scp(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Copy file(s) into your Envy.'
        subparser = subparsers.add_parser('scp', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument(
            'source', nargs='?', default=os.getcwd(),
            help='Local path to copy into your Envy.'
        )
        subparser.add_argument(
            'target', nargs='?', default='~/',
            help='Location in your Envy to place file(s). Non-absolute '
            'paths are interpreted relative to remote_user homedir.'
        )
        subparser.add_argument(
            '-n', '--name', action='store', default='',
            help='Specify custom name for an Envy.'
        )
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if not envy.ip():
            logging.error('Could not determine IP.')
            return

        host_string = '%s@%s' % (envy.config.remote_user, envy.ip())

        with fabric.api.settings(host_string=host_string):
            fabric.operations.put(
                args.source, args.target, mirror_local_mode=True
            )
