import unittest
from src.ui.test_window import TestWindow

class TestTimer(unittest.TestCase):
    def setUp(self):
        self.test_window = TestWindow()

    def test_timer_initialization(self):
        self.assertEqual(self.test_window.timer, 0)

    def test_start_timer(self):
        self.test_window.start_timer(60)
        self.assertGreater(self.test_window.timer, 0)

    def test_timer_countdown(self):
        self.test_window.start_timer(5)
        self.test_window.update_timer()  # Simulate a timer update
        self.assertLess(self.test_window.timer, 5)

    def test_timer_completion(self):
        self.test_window.start_timer(1)
        self.test_window.update_timer()  # Simulate a timer update
        self.test_window.update_timer()  # Simulate another update
        self.assertEqual(self.test_window.timer, 0)

if __name__ == '__main__':
    unittest.main()