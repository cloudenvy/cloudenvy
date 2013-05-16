# vim: tabstop=4 shiftwidth=4 softtabstop=4

import argparse
import logging
import pkgutil
import string

from cloudenvy.config import EnvyConfig

import cloudenvy.commands


#TODO(bcwaldon): replace this with entry points!
def _load_commands():
    """Iterate through modules in command and import suspected command classes

    This looks for a class in each module in cloudenvy.commands that has the
    same name as its module with the first character uppercased. For example,
    the cloudenvy.commands.up module should have a class Up within it.
    """
    modlist = list(pkgutil.iter_modules(cloudenvy.commands.__path__))
    #NOTE(bcwaldon): this parses out a string representation of each
    # individual command module. For example, if we had a single command
    # in cloudenvy.commands named 'up', this list would look like ['up]
    commands = [_[1] for _ in modlist]
    for command in commands:
        #NOTE(bcwaldon): the __import__ statement returns a handle on the
        # top-level 'cloudenvy' package, so we must iterate down through
        # each sub-package to get a handle on our module
        module_name = 'cloudenvy.commands.{0}'.format(command)
        _cloudenvy = __import__(module_name, globals(), locals(), [], -1)
        module = getattr(_cloudenvy.commands, command)

        command_class = getattr(module, string.capitalize(command))
        yield (command, command_class)


def _build_parser():
    parser = argparse.ArgumentParser(
        description='Launch a virtual machine on an OpenStack cloud.')
    parser.add_argument('-v', '--verbosity', action='count',
                        help='Increase output verbosity.')
    parser.add_argument('-c', '--cloud', action='store',
                        help='Specify which cloud to use.')
    return parser


def _init_help_command(parser, subparser):

    def find_command_help(config, args):
        if args.command:
            subparser.choices[args.command].print_help()
        else:
            parser.print_help()

    help_cmd = subparser.add_parser('help',
            help='Display help information for a specfiic command.')
    help_cmd.add_argument('command', action='store', nargs='?',
            help='Specific command to describe.')
    help_cmd.set_defaults(func=find_command_help)

    return parser


def _init_commands(commands, parser):
    _commands = {}
    for (command, command_class) in commands:
        _commands[command] = command_class(parser, _commands)


def main():
    parser = _build_parser()
    command_subparser = parser.add_subparsers(title='Available commands')
    _init_help_command(parser, command_subparser)

    commands = _load_commands()
    _init_commands(commands, command_subparser)

    args = parser.parse_args()
    config = EnvyConfig(args)

    if args.verbosity == 3:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('novaclient').setLevel(logging.DEBUG)
    elif args.verbosity == 2:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('novaclient').setLevel(logging.INFO)
    elif args.verbosity == 1:
        logging.getLogger().setLevel(logging.INFO)

    args.func(config, args)
