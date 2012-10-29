import logging

from cloudenvy.envy import Envy


class EnvyDestroy(object):
    """Power-off and destroy the current server."""

    def __init__(self, argparser):
        self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        subparser = subparsers.add_parser('destroy', help='ssh help')
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='specify custom name for an ENVy')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        if envy.find_server():
            envy.delete_server()
            logging.info('Deletion for `%s` has been initiated, it should be '
                         'deleted momentarily.' % envy.name)
            while envy.find_server():
                logging.info("... still waiting")
            logging.info("Done!")

        else:
            logging.error('There is no environment named %s' % envy.name)
