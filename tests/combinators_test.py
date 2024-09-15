import unittest

from combinators import *


class SequenceTest(unittest.TestCase):
    def test_correct_sequence(self):
        parser = exact(1) + exact(2) + exact(3)
        tokens = [1, 2, 3]
        cursor = TokenCursor(tokens)

        result = parser.run(cursor)
        print(result)
        self.assertTrue(result == Result.Ok(Maybe.Just([1, 2, 3])))
        


if __name__ == '__main__':
    unittest.main()