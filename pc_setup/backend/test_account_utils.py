import unittest

from account_utils import is_valid_mobile_phone, normalize_phone


class AccountUtilsTests(unittest.TestCase):
    def test_phone_is_stored_as_digits(self):
        self.assertEqual(normalize_phone("010-1234-5678"), "01012345678")

    def test_only_valid_010_mobile_number_is_accepted(self):
        self.assertTrue(is_valid_mobile_phone("010-1234-5678"))
        self.assertFalse(is_valid_mobile_phone("02-1234-5678"))


if __name__ == "__main__":
    unittest.main()
