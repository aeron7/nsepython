import unittest
from rahu import running_status

class TestStringMethods(unittest.TestCase):

    #region test running_status
    def test_running_status_after_market_hours(self):
        self.assertFalse(running_status())

    def test_running_status_during_market_hours(self):
        self.assertTrue(running_status())

    #endregion

if __name__ == '__main__':
    unittest.main()