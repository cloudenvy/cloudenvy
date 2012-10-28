import logging
import os
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
        subparser.add_argument('-s', '--scripts', default=None, nargs='*',
                               help='specify one or more provision scripts')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        logging.info('Running provision scripts for the `%s` ENVy...' %
                     envy.project_config['name'])
        if envy.ip():
            with fabric.api.settings(host_string=envy.ip(), user=envy.remote_user,
                                     forward_agent=True, disable_known_hosts=True):

                if args.scripts:
                    scripts = [os.path.expanduser(script) for
                               script in args.scripts]
                elif 'provision_scripts' in envy.project_config:
                    scripts = [os.path.expanduser(script) for script in
                               envy.project_config['provision_scripts']]
                elif 'provision_script_path' in envy.project_config:
                    provision_script = envy.project_config['provision_script_path']
                    scripts = [os.path.expanduser(provision_script)]
                else:
                    raise SystemExit('Please specify the path to your provision '
                                     'script(s) by either using the `--scripts` '
                                     'flag, or by defining the `provision_scripts`'
                                     ' config option in your Envyfile')

                for script in scripts:
                    logging.info('Running provision script from: %s', script)

                    for i in range(24):
                        try:
                            path = script
                            filename = os.path.basename(script)
                            remote_path = '~/%s' % filename
                            fabric.operations.run('if [ -e "$HOME/%s" ]; '
                                                  'then rm ~/%s; fi' %
                                                  (filename, filename))
                            fabric.operations.put(path, remote_path, mode=0755)
                            fabric.operations.run(remote_path)
                            break
                        except fabric.exceptions.NetworkError:
                            logging.error('Unable to upload the provision script '
                                          'from `%s`. Your ENVy is probably still '
                                          'booting. Trying again in 10 seconds.')
                            time.sleep(10)
                    logging.info('The provision script from `%s` has finished '
                                 'running.' % path)
        else:
            logging.error('Could not find IP.')
