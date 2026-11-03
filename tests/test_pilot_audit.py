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
    def test_chunk_contrast_allows_budget_change_but_rejects_extra_changes(self):
        meta={
            'pilot_e5_192':{'settings':{'total_token_budget':192,'device':'cpu','dtype':'torch.float32'},'batch_size':8},
            'pilot_e5_320':{'settings':{'total_token_budget':320,'device':'cpu','dtype':'torch.float32'},'batch_size':8}}
        signatures={key:('Python fixture',{'torch':'fixture-version'}) for key in meta}
        audit.validate_chunk_contrasts(meta,signatures)
        metadata_only=deepcopy(signatures)
        metadata_only['pilot_e5_192'][1]['sec-embedding-stability']='0.1.0'
        metadata_only['pilot_e5_320'][1]['sec-embedding-stability']='0.2.0'
        logged=audit.validate_chunk_contrasts(meta,metadata_only)
        self.assertEqual(logged[0]['project_version_a'],'0.1.0')
        self.assertEqual(logged[0]['project_version_b'],'0.2.0')
        for key,value in [('device','cuda'),('dtype','torch.float16')]:
            changed=deepcopy(meta)
            changed['pilot_e5_320']['settings'][key]=value
            with self.assertRaisesRegex(ValueError,'additional configuration'):
                audit.validate_chunk_contrasts(changed,signatures)
        changed=deepcopy(signatures)
        changed['pilot_e5_320']=('Other Python fixture',{'torch':'fixture-version'})
        with self.assertRaisesRegex(ValueError,'additional configuration'):
            audit.validate_chunk_contrasts(meta,changed)

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
