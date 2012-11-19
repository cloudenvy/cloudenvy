from cloudenvy.envy import Envy


class EnvySnapshot(object):

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        help_str = 'Snapshot your ENVy.'
        subparser = subparsers.add_parser('snapshot', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        return subparser

    #TODO(jakedahn): The entire UX for this needs to be talked about, refer to
    #                https://github.com/bcwaldon/cloudenvy/issues/27 for any
    #                discussion, if you're curious.
    def run(self, config, args):
        envy = Envy(config)
        envy.snapshot('%s-snapshot' % envy.name)
