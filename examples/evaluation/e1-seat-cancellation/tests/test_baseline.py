import unittest

from booking import Booking


class Baseline(unittest.TestCase):
    def test_reserve(self):
        booking = Booking(10, 2)
        self.assertEqual(booking.available, 8)
        self.assertEqual(booking.quantity, 2)
        self.assertEqual(booking.status, 'active')

    def test_cancel_once(self):
        booking = Booking(10, 2)
        booking.cancel()
        self.assertEqual(booking.available, 10)
        self.assertEqual(booking.status, 'cancelled')
