"""Exact combinatorial checks; no empirical independence assumption is asserted."""
import importlib.util
from itertools import combinations
from pathlib import Path
import sys
import unittest
import numpy as np

scripts=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(scripts))
spec=importlib.util.spec_from_file_location('peer_count',scripts/'peer_count_sensitivity.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PeerCountTests(unittest.TestCase):
    def test_uniform_reference_matches_exhaustive_enumeration(self):
        subsets=list(combinations(range(4),2))
        observed=np.mean([len(set(a)&set(b))/2 for a in subsets for b in subsets])
        expected,normalized=module.overlap_reference(5,2,observed)
        self.assertAlmostEqual(expected,observed)
        self.assertAlmostEqual(normalized,0)

    def test_identical_sets_have_normalized_excess_one(self):
        for k in [1,2,3,5]:self.assertAlmostEqual(module.overlap_reference(12,k,1)[1],1)

    def test_full_universe_and_invalid_overlap_rejected(self):
        for n,k,o in [(12,11,1),(12,0,0),(12,2,float('nan'))]:
            with self.assertRaises(ValueError):module.overlap_reference(n,k,o)


if __name__=='__main__':unittest.main()
