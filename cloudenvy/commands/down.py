import cloudenvy.envy


class Down(cloudenvy.envy.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Alias for `envy destroy`'
        subparser = subparsers.add_parser('down', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        return subparser

    def run(self, config, args):
        self.commands['destroy'].run(config, args)
