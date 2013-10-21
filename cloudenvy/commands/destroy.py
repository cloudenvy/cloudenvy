import logging

import cloudenvy.core


class Destroy(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Destroy an Envy.'
        subparser = subparsers.add_parser('destroy', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')

        #TODO(bcwaldon): design a better method for command aliases
        help_str = 'Alias for destroy command.'
        subparser = subparsers.add_parser('down', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')

        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if envy.find_server():
            envy.delete_server()
            logging.info('Deletion of Envy \'%s\' was triggered.' % envy.name)
            while envy.find_server():
                logging.info("... still waiting")
            logging.info("Done!")

        else:
            logging.error('Could not find Envy named \'%s\'.' % envy.name)
