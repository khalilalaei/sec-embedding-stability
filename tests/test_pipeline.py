"""Offline software checks only. Synthetic text is never research data."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from secstab.core import compare, normalize, peers, sha256, shared_chunks
from secstab.cli import corpus


class NumericalTests(unittest.TestCase):
    def test_normalization_rejects_failed_vectors(self):
        for vector in ([0, 0], [float('nan'), 1], [float('inf'), 1]):
            with self.assertRaises(ValueError):
                normalize(vector)

    def test_identical_peers_and_excluded_self(self):
        z = normalize(np.array([[1, 0], [1, .1], [0, 1], [.1, 1]]))
        s = z @ z.T
        chosen, _, margins = peers(s, 1)
        self.assertEqual(chosen[:, 0].tolist(), [1, 0, 3, 2])
        self.assertTrue(np.all(margins > 0))
        result = compare(s, s, list('abcd'), 1)
        self.assertEqual(result['mean_top_k_overlap'], 1)
        self.assertAlmostEqual(result['spearman_pair_similarity'], 1)

    def test_orthogonal_rotation_preserves_similarities(self):
        rng = np.random.default_rng(123)
        z = normalize(rng.normal(size=(9, 4)))
        q, _ = np.linalg.qr(rng.normal(size=(4, 4)))
        np.testing.assert_allclose(z @ z.T, (z @ q) @ (z @ q).T, atol=1e-12)

    def test_peer_switch_is_detected(self):
        a = np.array([[1,.9,.2,.1],[.9,1,.3,.2],[.2,.3,1,.8],[.1,.2,.8,1]])
        b = a.copy()
        b[0,1] = b[1,0] = .05
        result = compare(a, b, list('abcd'), 1)
        self.assertLess(result['mean_top_k_overlap'], 1)
        self.assertEqual(result['companies'][0]['peers_b'], ['c'])

    def test_invalid_k_and_matrix(self):
        for k in (0, 3, 4):
            with self.assertRaises(ValueError):
                peers(np.eye(4), k)
        with self.assertRaises(ValueError):
            peers(np.ones((3, 4)), 1)

    def test_ties_have_zero_margin(self):
        _, _, margin = peers(np.ones((4,4)), 1)
        np.testing.assert_array_equal(margin, np.zeros(4))

    def test_chunks_cover_exact_source_and_fit_all_counters(self):
        text = '  Alpha beta  gamma\nDelta  epsilon ' + 'q'*90 + ' end\n'
        fits = lambda s: len(s) <= 23 and len(s.encode('utf-8')) <= 25
        spans = shared_chunks(text, fits)
        self.assertEqual(''.join(text[a:b] for a,b in spans), text)
        self.assertEqual(spans[0][0], 0)
        self.assertEqual(spans[-1][1], len(text))
        self.assertTrue(all(fits(text[a:b]) for a,b in spans))
        self.assertTrue(all(spans[i][1] == spans[i+1][0] for i in range(len(spans)-1)))

    def test_unicode_source_offsets(self):
        text = 'risk café 中国 regulation risk🙂 growth'
        fits = lambda s: len(s.encode('utf-8')) <= 15
        spans = shared_chunks(text, fits)
        self.assertEqual(''.join(text[a:b] for a,b in spans), text)
        self.assertTrue(all(fits(text[a:b]) for a,b in spans))

    def test_empty_source_fails(self):
        with self.assertRaises(ValueError):
            shared_chunks('   ', lambda s: True)


class OfflinePipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        # Distinct synthetic software fixtures, not SEC or company observations.
        texts = ['bank loan credit capital '*10, 'bank loan deposit risk '*10,
                 'energy oil gas drilling '*10, 'energy oil fuel refining '*10]
        rows = []
        for i,text in enumerate(texts):
            raw, txt = self.root/f'raw{i}.html', self.root/f'text{i}.txt'
            raw.write_text('<html>synthetic unit-test source</html>')
            txt.write_text(text)
            rows.append({'document_id':str(i), 'cik':str(i),
                         'section':'Item 1A Risk Factors', 'review_status':'passed',
                         'raw_path':str(raw),'raw_sha256':sha256(raw),
                         'text_path':str(txt),'text_sha256':sha256(txt)})
        self.path = self.root/'corpus.json'
        self.path.write_text(json.dumps(rows))

    def tearDown(self):
        self.temp.cleanup()

    def cli(self,*args):
        return subprocess.run([sys.executable,'-m','secstab.cli',*args],
                              cwd=self.root, capture_output=True,text=True)

    def test_tfidf_compare_and_immutable_run(self):
        for name in ('a','b'):
            r = self.cli('tfidf','--corpus',str(self.path),'--run-id',name)
            self.assertEqual(r.returncode,0,r.stderr)
        r = self.cli('compare','--a','runs/a','--b','runs/b','--output','runs/check.json')
        self.assertEqual(r.returncode,0,r.stderr)
        result = json.loads((self.root/'runs/check.json').read_text())
        self.assertEqual(result['mean_top_k_overlap'],1)
        r = self.cli('tfidf','--corpus',str(self.path),'--run-id','a')
        self.assertNotEqual(r.returncode,0)

    def test_changed_run_output_rejected(self):
        for name in ('a','b'):
            r = self.cli('tfidf','--corpus',str(self.path),'--run-id',name)
            self.assertEqual(r.returncode,0,r.stderr)
        (self.root/'runs/a/peers.json').write_text('[]')
        r = self.cli('compare','--a','runs/a','--b','runs/b','--output','runs/check.json')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('hash changed',r.stderr)

    def test_source_tampering_rejected(self):
        (self.root/'text0.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'Changed text'):
            corpus(self.path)

    def test_pending_review_rejected(self):
        rows = json.loads(self.path.read_text())
        rows[0]['review_status'] = 'pending'
        self.path.write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError,'reviewed'):
            corpus(self.path)

    def test_ai_review_requires_explicit_scope_and_intact_source_map(self):
        rows = json.loads(self.path.read_text())
        proof = self.root/'source_map.json'
        proof.write_text('{"audit": "synthetic fixture"}')
        rows[0].update(review_status='ai_assisted_passed', reviewer='AI fixture',
                       source_map_path=str(proof),source_map_sha256=sha256(proof))
        self.path.write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError,'reviewed'):
            corpus(self.path)
        rows[0]['review_scope'] = 'descriptive_pilot_only'
        self.path.write_text(json.dumps(rows))
        self.assertEqual(len(corpus(self.path)[0]),4)
        proof.write_text('{}')
        with self.assertRaisesRegex(ValueError,'source map'):
            corpus(self.path)


if __name__ == '__main__':
    unittest.main()
