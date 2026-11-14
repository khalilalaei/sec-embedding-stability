"""Audit failure checks use synthetic fixtures, never downloaded prices."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import hashlib
import sys
import numpy as np
import pandas as pd

spec=importlib.util.spec_from_file_location('audit_market',Path(__file__).resolve().parents[1]/'scripts/audit_market_pilot.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class MarketAuditTests(unittest.TestCase):
    def fixture(self,root):
        dates=pd.bdate_range('2024-01-02',periods=5)
        corpus=[{'ticker':f'T{i}','document_id':f'd{i}','sec_name':f'Company{i}','sec_tickers':[f'T{i}']} for i in range(12)]
        (root/'provider_tables').mkdir()
        def write(name,obj):
            (root/name).write_text(json.dumps(obj))
        write('corpus.json',corpus);write('corpus_snapshot.json',corpus)
        write('evidence.json',{'corpus_sha256':module.sha(root/'corpus.json'),'documents':corpus})
        rows=[];sources={}
        for r in corpus:
            s=r['ticker'];prices=np.arange(100.,105.)
            frame=pd.DataFrame({'Date':dates.tz_localize('America/New_York'),'Open':prices,'High':prices+1,'Low':prices-1,'Close':prices,'Adj Close':prices,'Volume':100,'Dividends':0,'Stock Splits':0})
            name=f'provider_tables/{s}_history.csv';frame.to_csv(root/name,index=False);sources[name]=module.sha(root/name)
            name=f'provider_tables/{s}_metadata.json'
            write(name,{'symbol':s,'currency':'USD','instrumentType':'EQUITY','exchangeTimezoneName':'America/New_York'})
            sources[name]=module.sha(root/name)
            rows.extend({'date':str(d.date()),'security_id':'YF:'+s,'total_return':v} for d,v in zip(dates[1:],prices[1:]/prices[:-1]-1))
        pd.DataFrame(rows).to_csv(root/'returns.csv',index=False,float_format='%.17g')
        pd.DataFrame({'date':dates[1:]}).to_csv(root/'trading_calendar.csv',index=False)
        manifest={'status':'complete_data_collection_pending_review','corpus_sha256':module.sha(root/'corpus.json'),'source_files':sources,
            'outputs':{n:module.sha(root/n) for n in ['corpus_snapshot.json','returns.csv','trading_calendar.csv']},
            'completed_symbols':[r['ticker'] for r in corpus],'start_inclusive':'2024-01-01','end_exclusive':'2024-01-09'}
        write('manifest.json',manifest)
        return dates,manifest

    def run_audit(self,root,dates):
        calendar=SimpleNamespace(get_calendar=lambda *a,**kw:SimpleNamespace(sessions_in_range=lambda *a:dates))
        with patch.dict(sys.modules,{'exchange_calendars':calendar}),patch.object(module.importlib.metadata,'version',return_value='synthetic'):
            return module.audit(root,root/'corpus.json',root/'evidence.json')

    def test_valid_fixture_and_unhashed_source_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);dates,_=self.fixture(root)
            receipt,_,_=self.run_audit(root,dates)
            self.assertEqual(receipt['observations'],48)
            with (root/'provider_tables/T0_history.csv').open('a') as f:f.write('\n')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):self.run_audit(root,dates)

    def test_rehashed_but_incorrect_return_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);dates,manifest=self.fixture(root)
            frame=pd.read_csv(root/'returns.csv');frame.loc[0,'total_return']=0.5;frame.to_csv(root/'returns.csv',index=False)
            manifest['outputs']['returns.csv']=module.sha(root/'returns.csv');(root/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'returns differ'):self.run_audit(root,dates)

    def test_rehashed_calendar_omission_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);dates,manifest=self.fixture(root)
            pd.DataFrame({'date':dates[2:]}).to_csv(root/'trading_calendar.csv',index=False)
            manifest['outputs']['trading_calendar.csv']=module.sha(root/'trading_calendar.csv');(root/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'calendar mismatch'):self.run_audit(root,dates)


if __name__=='__main__':unittest.main()
