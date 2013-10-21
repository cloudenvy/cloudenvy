import logging

import fabric.api
import fabric.operations

import cloudenvy.core


class Ssh(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'SSH into your Envy.'
        subparser = subparsers.add_parser('ssh', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if envy.ip():
            disable_known_hosts = ('-o UserKnownHostsFile=/dev/null'
                                   ' -o StrictHostKeyChecking=no')
            forward_agent = '-o ForwardAgent=yes'

            options = [disable_known_hosts]
            if envy.config.forward_agent:
                options.append(forward_agent)

            fabric.operations.local('ssh %s %s@%s' % (' '.join(options),
                                                      envy.config.remote_user,
                                                      envy.ip()))
        else:
            logging.error('Could not determine IP.')
