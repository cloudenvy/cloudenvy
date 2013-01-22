import logging
import time
import os

import fabric.api
import fabric.operations

from cloudenvy.envy import Envy


class EnvyFiles(object):

    def __init__(self, argparser=None):
        if argparser:
            self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        help_str = 'Upload arbitrary files from your local machine to an ' \
                   'ENVy. Uses the `files` hash in your Envyfile. Mirrors ' \
                   'the local mode of the file.'
        subparser = subparsers.add_parser('files', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an ENVy.')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        if 'files' in envy.project_config:
            if envy.ip():
                host_string = '%s@%s' % (envy.remote_user, envy.ip())

                with fabric.api.settings(host_string=host_string):
                    file_list = [(os.path.expanduser(filename), location) for
                                 filename, location in
                                 envy.project_config['files'].iteritems()]

                    for filename, endlocation in file_list:
                        logging.info("Putting file from '%s' to '%s'",
                                     filename, endlocation)

                        for i in range(24):
                            try:
                                fabric.operations.put(filename, endlocation,
                                                      mirror_local_mode=True,
                                                      use_sudo=True)
                                break
                            except fabric.exceptions.NetworkError:
                                logging.debug('Unable to upload the file ' \
                                              'from `%s`. Your ENVy is ' \
                                              'probably still booting. Trying '\
                                              'again in 10 seconds.' % filename)
                                time.sleep(10)

            else:
                logging.error('Could not determine IP.')
