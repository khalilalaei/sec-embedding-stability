"""Synthetic extractor regression tests, not evidence about real filings."""
import importlib.util
import unittest

from secstab.extraction import extract


@unittest.skipUnless(importlib.util.find_spec('lxml'), 'Install .[extract] for parser tests')
class ExtractionTests(unittest.TestCase):
    def fixture(self, heading='ITEM 1A. RISK FACTORS', following='ITEM 1B. UNRESOLVED STAFF COMMENTS'):
        body = '<p>Material operational risks include supplier and currency exposure.</p>'*110
        return ('<html><head><title>Not filing text</title></head><body>'
                '<p>Item 1A.</p><p>Risk Factors</p><p>9</p>'
                '<p>Item 1B.</p><p>Unresolved Staff Comments</p><p>20</p>'
                f'<h2>{heading}</h2>{body}<h2>{following}</h2>'
                '<p>OUTSIDE SECTION</p></body></html>').encode()

    def test_reject_contents_and_preserve_repeated_substantive_text(self):
        text, evidence = extract(self.fixture())
        self.assertTrue(text.startswith('ITEM 1A. RISK FACTORS'))
        self.assertEqual(text.count('Material operational risks'), 110)
        self.assertNotIn('OUTSIDE SECTION', text)
        self.assertEqual(len(evidence['rejected_candidates']), 1)

    def test_split_deere_style_headings(self):
        text, evidence = extract(self.fixture('ITEM 1A.</h2><p>RISK FACTORS.',
                                             'ITEM 1B.</h2><p>UNRESOLVED STAFF COMMENTS.'))
        self.assertTrue(text.startswith('ITEM 1A.\n\nRISK FACTORS.'))
        self.assertEqual(evidence['following_heading'], 'ITEM 1B.')

    def test_hidden_text_is_excluded_but_visible_tail_retained(self):
        raw = self.fixture().replace(b'<h2>ITEM 1B.',
            b'<div style="display: none">HIDDEN_FAILURE</div>VISIBLE TAIL'
            b'<ix:hidden>HIDDEN_FAILURE</ix:hidden><h2>ITEM 1B.')
        text, _ = extract(raw)
        self.assertNotIn('HIDDEN_FAILURE', text)
        self.assertIn('VISIBLE TAIL', text)

    def test_inline_words_and_entities_preserved(self):
        raw = self.fixture().replace(b'<h2>ITEM 1B.',
            b'<p>cyber<b>security</b> &amp; currency <span>risks</span>.</p><h2>ITEM 1B.')
        text, _ = extract(raw)
        self.assertIn('cybersecurity & currency risks.', text)

    def test_cleanup_logged_and_source_ranges_reconstruct_lines(self):
        raw = self.fixture().replace(b'<h2>ITEM 1B.',
            b'<p>14</p><p>Table of Contents</p><p>PART I</p><h2>ITEM 1B.')
        text, evidence = extract(raw)
        self.assertEqual(sum(evidence['cleaning_counts'].values()), 3)
        for row in evidence['retained_lines']:
            self.assertEqual(text[row['output_start']:row['output_end']], row['text'])
        self.assertTrue(all(fragment['xpath'] for fragment in evidence['source_fragments']))

    def test_missing_end_heading_fails(self):
        with self.assertRaises(ValueError):
            extract(self.fixture(following='ITEM 2. PROPERTIES'))

    def test_ambiguous_multiple_sections_fail(self):
        raw = self.fixture()
        other = '<h2>ITEM 1A. RISK FACTORS</h2>'+'<p>Another material risk.</p>'*300+'<h2>ITEM 1B. UNRESOLVED STAFF COMMENTS</h2>'
        with self.assertRaises(ValueError):
            extract(raw.replace(b'</body>', other.encode()+b'</body>'))


if __name__ == '__main__':
    unittest.main()
