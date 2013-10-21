import logging
import time
import os

import fabric.api
import fabric.operations

import cloudenvy.core


class Files(cloudenvy.core.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Upload arbitrary files from your local machine to an ' \
                   'Envy. Uses the `files` hash in your Envyfile. Mirrors ' \
                   'the local mode of the file.'
        subparser = subparsers.add_parser('files', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)
        subparser.add_argument('-n', '--name', action='store', default='',
                               help='Specify custom name for an Envy.')
        return subparser

    def run(self, config, args):
        envy = cloudenvy.core.Envy(config)

        if envy.ip():
            host_string = '%s@%s' % (envy.config.remote_user, envy.ip())

            with fabric.api.settings(host_string=host_string):
                use_sudo = envy.config.project_config.get('files_use_sudo', True)
                files = envy.config.project_config.get('files', {}).items()
                files = [(os.path.expanduser(loc), rem) for loc, rem in files]

                for local_path, remote_path in files:
                    logging.info("Copying file from '%s' to '%s'",
                                 local_path, remote_path)

                    if not os.path.exists(local_path):
                        logging.error("Local file '%s' not found.", local_path)

                    dest_dir = _parse_directory(remote_path)
                    if dest_dir:
                        self._create_directory(dest_dir)
                    self._put_file(local_path, remote_path, use_sudo)

        else:
            logging.error('Could not determine IP.')

    def _create_directory(self, remote_dir):
        for i in range(24):
            try:
                fabric.operations.run('mkdir -p %s' % remote_dir)
                break
            except fabric.exceptions.NetworkError:
                logging.debug("Unable to create directory '%s'. "
                              "Trying again in 10 seconds." % remote_dir)
                time.sleep(10)

    def _put_file(self, local_path, remote_path, use_sudo):
        for i in range(24):
            try:
                fabric.operations.put(local_path, remote_path,
                                      mirror_local_mode=True,
                                      use_sudo=use_sudo)
                break
            except fabric.exceptions.NetworkError as err:
                logging.debug("Unable to upload the file from '%s': %s. "
                              "Trying again in 10 seconds." %
                              (local_path, err))
                time.sleep(10)


def _parse_directory(path):
    """Given a valid unix path, return the directory

    This will not expand a ~ to a home directory or
    prepend that home directory to a relative path.
    """
    if path is None or '/' not in path:
        return None
    else:
        return os.path.dirname(path)
