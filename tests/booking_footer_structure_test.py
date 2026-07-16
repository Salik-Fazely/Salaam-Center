import unittest
from pathlib import Path

from tests.commercial_truth_test import StructureParser


ROOT = Path(__file__).resolve().parents[1]


class BookingFooterStructureTests(unittest.TestCase):
    def test_booking_footer_markup_is_balanced(self):
        parser = StructureParser()
        parser.feed((ROOT / "book-trial/index.html").read_text(encoding="utf-8"))
        parser.close()

        self.assertEqual([], parser.errors)


if __name__ == "__main__":
    unittest.main()
