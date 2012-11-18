from cloudenvy.envy import Envy


class EnvySnapshot(object):
    """Create a snapshot of an ENVy."""

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        subparser = subparsers.add_parser('snapshot', help='snapshot help')
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an ENVy.')

        return subparser

    def run(self, config, args):
        envy = Envy(config)
        envy.snapshot('%s-snapshot' % envy.name)
