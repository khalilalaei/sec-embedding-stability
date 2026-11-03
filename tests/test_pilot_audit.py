"""Checks that the offline audit fails on corrupted or unsafe evidence."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile
from copy import deepcopy
import numpy as np

spec=importlib.util.spec_from_file_location('pilot_audit_script',Path(__file__).resolve().parents[1]/'scripts/audit_pilot_results.py')
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class PilotAuditTests(unittest.TestCase):
    def test_archive_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            archive=root/'bad.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape.txt','not allowed')
            with self.assertRaisesRegex(ValueError,'escapes'):
                audit.unpack(archive,root/'extract')
            self.assertFalse((root/'escape.txt').exists())

    def test_windows_path_separator_is_normalized(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            archive=root/'windows.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('runs\\example\\manifest.json','{}')
            audit.unpack(archive,root/'extract')
            self.assertEqual((root/'extract/runs/example/manifest.json').read_text(),'{}')

    def test_changed_summary_metric_is_rejected(self):
        a=np.array([[1,.9,.3,.2],[.9,1,.4,.1],[.3,.4,1,.8],[.2,.1,.8,1]])
        actual=audit.recompute_comparison(a,a,list('abcd'))
        tampered=deepcopy(actual)
        tampered['mean_top_k_overlap']=.5
        with self.assertRaisesRegex(ValueError,'Comparison mismatch'):
            audit.check_comparison(tampered,actual)

    def test_wrong_peer_order_rejected_even_with_same_set_and_metrics(self):
        a=np.array([[1,.9,.3,.2],[.9,1,.4,.1],[.3,.4,1,.8],[.2,.1,.8,1]])
        actual=audit.recompute_comparison(a,a,list('abcd'))
        tampered=deepcopy(actual)
        tampered['companies'][0]['peers_b'].reverse()
        with self.assertRaisesRegex(ValueError,'Peer mismatch'):
            audit.check_comparison(tampered,actual)


if __name__=='__main__':unittest.main()
