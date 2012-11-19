import logging
import os
import time

import fabric.api
import fabric.operations

from cloudenvy.envy import Envy


class EnvyProvision(object):

    def __init__(self, argparser=None):
        if argparser:
            self._build_subparser(argparser)

    def _build_subparser(self, subparsers):
        help_str = 'Uplaod and execute script(s) in your ENVy.'
        subparser = subparsers.add_parser('provision', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an ENVy.')
        subparser.add_argument('-s', '--scripts', nargs='*', metavar='PATH',
                               help='Specify one or more scripts.')
        return subparser

    def run(self, config, args):
        envy = Envy(config)

        logging.info('Running provision scripts for ENVy \'%s\'.' %
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
                                     ' config option in your Envyfile.')

                for script in scripts:
                    logging.info('Running provision script from \'%s\'', script)

                    for i in range(24):
                        try:
                            path = script
                            filename = os.path.basename(script)
                            remote_path = '~/%s' % filename
                            fabric.operations.put(path, remote_path, mode=0755)
                            fabric.operations.run(remote_path)
                            break
                        except fabric.exceptions.NetworkError:
                            logging.debug('Unable to upload the provision script '
                                          'from `%s`. Your ENVy is probably still '
                                          'booting. Trying again in 10 seconds.' % path)
                            time.sleep(10)
                    logging.info('Provision script \'%s\' finished.' % path)
        else:
            logging.error('Could not determine IP.')
