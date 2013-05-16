import logging
import os

import cloudenvy.envy


project_file = """project_config:
  name: %(name)s

  # ID or name of image
  image: %(image)s

  # Remote VM user
  #remote_user: ubuntu

  # Compute flavor to use
  #flavor_name: m1.small

  # Control automatic provisioning of environment
  #auto_provision: False

  # List of scripts used to provision environment
  #provision_scripts:
  #  - provision.sh
"""


class Init(cloudenvy.envy.Command):

    def _build_subparser(self, subparsers):
        help_str = 'Initialize a new CloudEnvy project.'
        subparser = subparsers.add_parser('init', help=help_str,
                                          description=help_str)
        subparser.set_defaults(func=self.run)

        subparser.add_argument('-n', '--name', required=True,
                help='Name of new CloudEnvy project')
        subparser.add_argument('-i', '--image', required=True,
                help='Name or ID of image to use for CloudEnvy project')

        return subparser

    def run(self, config, args):
        paths = [
            'Envyfile',
            'Envyfile.yml',
        ]

        for path in paths:
            if os.path.isfile(path):
                logging.error("A project file already exists. Please "
                              "remove %s it and run init again." % path)

        with open('Envyfile.yml', 'w') as fap:
            fap.write(project_file % {'name': args.name, 'image': args.image})

        logging.info("Created Envyfile.yml for new project '%s'", args.name)
