#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest
from fd_import import tokenizer as tk
from fd_import.tokenizer import ChunkType

class TestsTokenizer(unittest.TestCase):
    def test_commas_are_detected(self):
        chunks = tk.tokenize('foo, bar')
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0][0], ChunkType.Word)
        self.assertEqual(chunks[1][0], ChunkType.Comma)
        self.assertEqual(chunks[2][0], ChunkType.Word)

    def test_semicolons_are_detected(self):
        chunks = tk.tokenize('foo; bar')
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0][0], ChunkType.Word)
        self.assertEqual(chunks[1][0], ChunkType.Semicolon)
        self.assertEqual(chunks[2][0], ChunkType.Word)

    def test_vert_bar_detected(self):
        chunks = tk.tokenize('foo | bar')
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0][0], ChunkType.Word)
        self.assertEqual(chunks[1][0], ChunkType.VerticalBar)
        self.assertEqual(chunks[2][0], ChunkType.Word)

    def test_parenthesized_expressions_parsed_corretly(self):
        tks = tk.tokenize('test (the) behaviour')
        self.assertEqual(len(tks), 3)
        self.assertEqual(tks[0][0], ChunkType.Word)
        self.assertEqual(tks[1][0], ChunkType.Paren)
        self.assertEqual(tks[1][1], 'the')
        self.assertEqual(tks[2][0], ChunkType.Word)
        # now paren at beginning
        tks = tk.tokenize('(the) behaviour')
        self.assertEqual(len(tks), 2)
        self.assertEqual(tks[0][0], ChunkType.Paren)
        self.assertEqual(tks[0][1], 'the')
        self.assertEqual(tks[1][0], ChunkType.Word)
        # now at the end
        tks = tk.tokenize('fond (of)')
        self.assertEqual(len(tks), 2)
        self.assertEqual(tks[0][0], ChunkType.Word)
        self.assertEqual(tks[1][0], ChunkType.Paren)
        self.assertEqual(tks[1][1], 'of')

    def test_braces_recognized(self):
        tks = tk.tokenize('test {blah} behaviour')
        self.assertEqual(len(tks), 3)
        self.assertEqual(tks[0][0], ChunkType.Word)
        self.assertEqual(tks[1][0], ChunkType.Brace)
        self.assertEqual(tks[1][1], 'blah')
        self.assertEqual(tks[2][0], ChunkType.Word)
        # now paren at beginning
        tks = tk.tokenize('{schnurp} xyz')
        self.assertEqual(len(tks), 2)
        self.assertEqual(tks[0][0], ChunkType.Brace)
        self.assertEqual(tks[1][0], ChunkType.Word)
        self.assertEqual(tks[0][1], 'schnurp')
        # now at the end
        tks = tk.tokenize('Fleisch {n}')
        self.assertEqual(len(tks), 2)
        self.assertEqual(tks[0][0], ChunkType.Word)
        self.assertEqual(tks[1][0], ChunkType.Brace)
        self.assertEqual(tks[1][1], 'n')

    def test_brackets_recognized(self):
        tks = tk.tokenize('test [Br.] behaviour')
        self.assertEqual(len(tks), 3)
        self.assertEqual(tks[0][0], ChunkType.Word)
        self.assertEqual(tks[1][0], ChunkType.Bracket)
        self.assertEqual(tks[1][1], 'Br.')
        self.assertEqual(tks[2][0], ChunkType.Word)
        # now paren at beginning
        tks = tk.tokenize('[zool.] xyz')
        self.assertEqual(len(tks), 2)
        self.assertEqual(tks[0][0], ChunkType.Bracket)
        self.assertEqual(tks[1][0], ChunkType.Word)
        self.assertEqual(tks[0][1], 'zool.')
        # now at the end
        tks = tk.tokenize('Fleisch [bot.]')
        self.assertEqual(len(tks), 2)
        self.assertEqual(tks[0][0], ChunkType.Word)
        self.assertEqual(tks[1][0], ChunkType.Bracket)
        self.assertEqual(tks[1][1], 'bot.')

    def test_enclosing_chars_have_precedence_over_delimiters(self):
        tks = tk.tokenize('(a,b;c|d/e) {a,b;c|d/e} [a,b;c|d/e]')
        self.assertEqual(len(tks), 3)
        for chunk in tks:
            self.assertEqual(chunk[1], 'a,b;c|d/e')
        # test slash
        tks = tk.tokenize('x /a,b;c|d/ y', parse_slash=True)
        self.assertEqual(len(tks), 3)
        self.assertEqual(tks[1][1], 'a,b;c|d')

    def test_paren_or_slashes_in_words_ignored(self):
        tks = tk.tokenize('house(s), Häuser/innen', parse_slash=True)
        self.assertEqual(len(tks), 3)
        self.assertEqual(tks[0][0], ChunkType.Word)
        self.assertEqual(tks[2][0], ChunkType.Word)

    def test_slash_within_paren_works(self):
        tks = tk.tokenize('(my/example)')
        self.assertEqual(len(tks), 1)
        self.assertEqual(tks[0][0], ChunkType.Paren)
        tks = tk.tokenize('(my/example)', parse_slash=True)
        self.assertEqual(len(tks), 1, "expected one element, got: " + repr(tks))
        self.assertEqual(tks[0][0], ChunkType.Paren)

    def test_only_expressions_with_no_spaces_withing_slash_slash_parsed(self):
        tks = tk.tokenize('/AB/', parse_slash=True)
        self.assertEqual(len(tks), 1)
        self.assertEqual(tks[0][0], ChunkType.Slash)
        tks = tk.tokenize('A / B/', parse_slash=True)
        self.assertEqual(len(tks), 1)
        self.assertEqual(tks[0][0], ChunkType.Word)

    def test_slash_takes_precedence_over_brackets(self):
        tks = tk.tokenize('/{/', parse_slash=True)
        self.assertEqual(len(tks), 1)
        self.assertEqual(tks[0][1], '{')
        
        
     
 

if __name__ == '__main__':
    unittest.main()
