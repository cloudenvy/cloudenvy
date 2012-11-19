import logging

from cloudenvy.envy import Envy


class EnvyDestroy(object):

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        help_str = 'Destroy an ENVy.'
        subparser = subparsers.add_parser('destroy', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an ENVy.')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        if envy.find_server():
            envy.delete_server()
            logging.info('Deletion of ENVy \'%s\' was triggered.' % envy.name)
            while envy.find_server():
                logging.info("... still waiting")
            logging.info("Done!")

        else:
            logging.error('Could not find ENVy named \'%s\'.' % envy.name)
