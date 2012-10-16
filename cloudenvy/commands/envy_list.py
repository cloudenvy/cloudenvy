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

    #TODO(jakedahn): The way this works is just silly. This should be totally
    #                refactored to use nova's server metadata attributes.
    def run(self, config, args):
        envy = Envy(config)
        envys = []
        servers = envy.list_servers()

        for server in servers:
            if len(server.name.split(envy.name)) > 1:
                envys.append(str(server.name))
        print "ENVys for your project: %s" % str(envys)
