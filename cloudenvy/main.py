# vim: tabstop=4 shiftwidth=4 softtabstop=4

import argparse
import logging

from cloudenvy.config import EnvyConfig

from cloudenvy.commands.envy_up import EnvyUp
from cloudenvy.commands.envy_list import EnvyList
from cloudenvy.commands.envy_provision import EnvyProvision
from cloudenvy.commands.envy_snapshot import EnvySnapshot
from cloudenvy.commands.envy_ip import EnvyIP
from cloudenvy.commands.envy_scp import EnvySCP
from cloudenvy.commands.envy_dotfiles import EnvyDotfiles
from cloudenvy.commands.envy_ssh import EnvySSH
from cloudenvy.commands.envy_destroy import EnvyDestroy
from cloudenvy.commands.envy_run import EnvyRun


def _build_parser():
    parser = argparse.ArgumentParser(
        description='Launch a virtual machine in an openstack environment.')
    parser.add_argument('-v', '--verbosity', action='count',
                        help='increase output verbosity')
    parser.add_argument('-c', '--cloud', action='store',
                        help='specify which cloud to use')
    subparsers = parser.add_subparsers(title='Available commands:')

    # Load up all of the subparser classes
    EnvyUp(subparsers)
    EnvyList(subparsers)
    EnvyProvision(subparsers)
    EnvySnapshot(subparsers)
    EnvyIP(subparsers)
    EnvySCP(subparsers)
    EnvyDotfiles(subparsers)
    EnvySSH(subparsers)
    EnvyDestroy(subparsers)
    EnvyRun(subparsers)

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    config = EnvyConfig(args).get_config()

    if args.verbosity == 3:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('novaclient').setLevel(logging.DEBUG)
    elif args.verbosity == 2:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('novaclient').setLevel(logging.INFO)
    elif args.verbosity == 1:
        logging.getLogger().setLevel(logging.INFO)

    args.func(config, args)
