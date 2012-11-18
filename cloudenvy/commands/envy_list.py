from cloudenvy.envy import Envy


class EnvyList(object):
    """List all ENVys in context of your current project"""

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        subparser = subparsers.add_parser('list', help='list help')
        subparser.set_defaults(func=self.run)
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='specify custom name for an ENVy')

        return subparser

    def run(self, config, args):
        envy = Envy(config)

        for server in envy.list_servers():
            if server.name.startswith(envy.name):
                print server.name
