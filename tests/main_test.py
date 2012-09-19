import unittest

import mock
import fabric.exceptions

from cloudenvy import exceptions
from cloudenvy import main


class UpTests(unittest.TestCase):
    def setUp(self):
        cl = ['up']
        self.args = main._build_parser().parse_args(cl)

    def test_basic(self):
        with mock.patch('cloudenvy.template.Template') as m:
            instance = m.return_value
            instance.server.return_value = None
            instance.build_server.return_value = None
            instance.ip.return_value = '10.0.0.1'

        main.up(self.args)
        instance.build_server.assert_called_once_with()
        instance.ip.assert_called_with()

    def test_no_image(self):
        with mock.patch('cloudenvy.template.Template') as m:
            instance = m.return_value
            instance.server.return_value = None
            instance.build_server.side_effect = exceptions.ImageNotFound()

            main.up(self.args)

            instance.build_server.assert_called_once_with()
            assert not instance.ip.called

    def test_no_ips(self):
        with mock.patch('cloudenvy.template.Template') as m:
            instance = m.return_value
            instance.server.return_value = None
            instance.build_server.side_effect = exceptions.NoIPsAvailable()

            main.up(self.args)

            instance.build_server.assert_called_once_with()
            assert not instance.ip.called

    def test_already_up(self):
        with mock.patch('cloudenvy.template.Template') as m:
            instance = m.return_value
            instance.server.return_value = True
            instance.ip.return_value = '10.0.0.1'

            main.up(self.args)

            assert instance.ip.called


class DestroyTests(unittest.TestCase):
    def setUp(self):
        cl = ['destroy']
        self.args = main._build_parser().parse_args(cl)

    @mock.patch('time.sleep', lambda x: None)
    def test_basic(self):
        with mock.patch('cloudenvy.template.Template') as m:
            instance = m.return_value
            instance.find_server.side_effect = [True] * 5 + [False]
            instance.delete_server.return_value = None

            main.destroy(self.args)

            assert instance.delete_server.called
            assert instance.find_server.call_count == 6

    def test_no_server(self):
        with mock.patch('cloudenvy.template.Template') as m:
            instance = m.return_value
            instance.find_server.return_value = False

            main.destroy(self.args)

            assert not instance.delete_server.called
            assert instance.find_server.call_count == 1


class IpTests(unittest.TestCase):
    def setUp(self):
        cl = ['ip']
        self.args = main._build_parser().parse_args(cl)

    def test_basic(self):
        with mock.patch('cloudenvy.template.Template') as m:
            instance = m.return_value
            instance.server.return_value = True
            instance.ip.return_value = '10.0.0.1'

            main.ip(self.args)

            assert instance.server.called
            assert instance.ip.called

    def test_no_ip(self):
        with mock.patch('cloudenvy.template.Template') as m:
            instance = m.return_value
            instance.server.return_value = True
            instance.ip.return_value = None

            main.ip(self.args)

            assert instance.server.called
            assert instance.ip.called

    def test_no_server(self):
        with mock.patch('cloudenvy.template.Template') as m:
            instance = m.return_value
            instance.find_server.return_value = False

            main.destroy(self.args)

            assert not instance.delete_server.called
            assert instance.find_server.call_count == 1


class ProvisionTests(unittest.TestCase):
    def setUp(self):
        cl = ['provision']
        self.args = main._build_parser().parse_args(cl)

    @mock.patch('time.sleep', lambda x: None)
    @mock.patch('cloudenvy.cloud.CloudAPI', mock.MagicMock())
    def test_basic(self):
        with mock.patch('fabric.operations') as m:
            m.put.side_effect = [fabric.exceptions.NetworkError()] * 5 + [True]
            m.run.return_value = False

            main.provision(self.args)

            assert m.put.call_count == 6
            assert m.run.called
