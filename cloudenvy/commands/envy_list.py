from cloudenvy.envy import Envy


class EnvyList(object):

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        help_str = 'List all ENVys in your current project.'
        subparser = subparsers.add_parser('list', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an ENVy.')

        return subparser

    def run(self, config, args):
        envy = Envy(config)

        for server in envy.list_servers():
            if server.name.startswith(envy.name):
                print server.name
