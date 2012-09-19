import unittest

from cloudenvy import main


class ParserTests(unittest.TestCase):
    """Basic tests to keep track of changes to our parser."""

    def setUp(self):
        super(ParserTests, self).setUp()
        self.parser = main._build_parser()

    def test_general(self):
        cloud = 'somecloud'
        name = 'somename'
        cl = ['-c', cloud, '-n', name, 'up']
        args = self.parser.parse_args(cl)
        self.assertEqual(args.func, main.up)

        # check flags
        self.assertEqual(args.cloud, cloud)
        self.assertEqual(args.name, name)

    def test_destroy(self):
        cl = ['destroy']
        args = self.parser.parse_args(cl)
        self.assertEqual(args.func, main.destroy)

    def test_ip(self):
        cl = ['ip']
        args = self.parser.parse_args(cl)
        self.assertEqual(args.func, main.ip)

    def test_provision(self):
        userdata = 'somefile'
        remote_user = 'remote'
        cl = ['provision', '-u', userdata, '-r', remote_user]
        args = self.parser.parse_args(cl)
        self.assertEqual(args.func, main.provision)

        # check flags
        self.assertEqual(args.remote_user, remote_user)
        self.assertEqual(args.userdata, userdata)

    def test_ssh(self):
        cl = ['ssh']
        args = self.parser.parse_args(cl)
        self.assertEqual(args.func, main.ssh)

    def test_up(self):
        userdata = 'somefile'
        cl = ['up', '-p', '-u', userdata]
        args = self.parser.parse_args(cl)
        self.assertEqual(args.func, main.up)

        # check flags
        self.assertEqual(args.provision, True)
        self.assertEqual(args.userdata, userdata)
