import cloudenvy.envy


class Snapshot(cloudenvy.envy.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Snapshot your ENVy.'
        subparser = subparsers.add_parser('snapshot', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an ENVy.')

        return subparser

    def run(self, config, args):
        envy = cloudenvy.envy.Envy(config)
        envy.snapshot('%s-snapshot' % envy.name)
