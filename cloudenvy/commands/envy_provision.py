import logging
import time

import fabric.api
import fabric.operations

from cloudenvy.envy import Envy


class EnvyProvision(object):
    """Run a provision script to setup your ENVy"""

    def __init__(self, argparser=None):
        if argparser:
            self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        subparser = subparsers.add_parser('provision', help='provision help')
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='specify custom name for an ENVy')
        subparser.add_argument('-u', '--userdata', action='store',
                               help='specify the location of userdata')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        logging.info('Starting provisioning of the `%s` ENVy...' %
                     envy.project_config['name'])

        try:
            local_path = envy.project_config['provision_script_path']
            remote_path = '~/provision_script'
        except KeyError:
            raise SystemExit('Please specify which provision script should be '
                             'used by passing in `-u` to the provision '
                             'command, or by defining `provision_script_path`'
                             'in ./Envyfile')

        logging.info('Using provision script from: %s', local_path)

        with fabric.api.settings(host_string=envy.ip(),
                                 user=envy.remote_user,
                                 forward_agent=True,
                                 disable_known_hosts=True):
            for i in range(12):
                try:
                    fabric.operations.run('if [ -e "$HOME/provision_script" ];'
                                          ' then rm ~/provision_script; fi')
                    fabric.operations.put(local_path,
                                          remote_path,
                                          mode=0755)
                    break
                except fabric.exceptions.NetworkError:
                    logging.error('Unable to upload your provision script. '
                                  'Your ENVy instance is probably not yet '
                                  'built. Trying again in 10 seconds.')
                    time.sleep(10)
            fabric.operations.run(remote_path)
        logging.info('The provision script from `%s` has finished running.' %
                     local_path)
