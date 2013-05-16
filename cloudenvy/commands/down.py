from cloudenvy.commands.destroy import EnvyDestroy


class EnvyDown(object):

    def __init__(self, argparser):
        self.argparser = argparser
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        help_str = 'Alias for `envy destroy`'
        subparser = subparsers.add_parser('down', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        return subparser

    def run(self, config, args):
        EnvyDestroy(self.argparser).run(config, args)
