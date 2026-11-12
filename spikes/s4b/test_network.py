import unittest
from types import SimpleNamespace

from run_engine import validate_network


def output(text='', code=0):
    return SimpleNamespace(stdout=text, returncode=code)


class NetworkObservationTests(unittest.TestCase):
    def test_only_loopback_and_no_default_routes_accepted(self):
        self.assertEqual(validate_network(output('1: lo: <LOOPBACK>\n'), output(), output())['interfaces'], ['lo'])

    def test_non_eth0_interfaces_and_unknown_output_denied(self):
        for text in ('1: lo: <LOOPBACK>\n2: enp1s0: <UP>\n', '1: lo: <LOOPBACK>\n2: wlan0: <UP>\n', 'unparseable'):
            with self.assertRaises(AssertionError):
                validate_network(output(text), output(), output())

    def test_default_dev_and_ipv6_default_forms_denied(self):
        for text in ('default dev enp1s0', '0.0.0.0/0 dev lo', '::/0 dev lo', 'default via ::1 dev lo'):
            with self.assertRaises(AssertionError):
                validate_network(output('1: lo: <LOOPBACK>'), output(text), output())
            with self.assertRaises(AssertionError):
                validate_network(output('1: lo: <LOOPBACK>'), output(), output(text))

    def test_each_failed_command_is_denied(self):
        for index in range(3):
            values = [output('1: lo: <LOOPBACK>'), output(), output()]
            values[index].returncode = 1
            with self.assertRaises(AssertionError):
                validate_network(*values)
