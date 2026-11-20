"""Run with: python -m unittest discover -s tests"""
import unittest
from unittest.mock import patch
from security import verify_bearer_header, SecurityConfigurationError


class BearerTokenTests(unittest.TestCase):
    def setUp(self):
        self.token = "a" * 48

    def test_correct_token(self):
        self.assertTrue(verify_bearer_header("Bearer " + self.token, token=self.token))

    def test_case_insensitive_scheme(self):
        self.assertTrue(verify_bearer_header("bearer " + self.token, token=self.token))

    def test_wrong_token(self):
        self.assertFalse(verify_bearer_header("Bearer " + "b" * 48, token=self.token))

    def test_missing_header(self):
        self.assertFalse(verify_bearer_header(None, token=self.token))

    def test_missing_scheme(self):
        self.assertFalse(verify_bearer_header(self.token, token=self.token))

    def test_short_secret_fails_closed(self):
        with self.assertRaises(SecurityConfigurationError):
            verify_bearer_header("Bearer abc", token="abc")

    def test_missing_secret_fails_closed(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(SecurityConfigurationError):
                verify_bearer_header(None)

    def test_empty_supplied_token(self):
        self.assertFalse(verify_bearer_header("Bearer ", token=self.token))


if __name__ == "__main__":
    unittest.main()
