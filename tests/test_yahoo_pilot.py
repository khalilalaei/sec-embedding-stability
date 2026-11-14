"""Synthetic provider fixtures only; no live Yahoo requests or market findings."""
import unittest
from collections.abc import Mapping
from types import SimpleNamespace
import json
import argparse
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
from unittest.mock import patch
import numpy as np
import pandas as pd
from secstab.yahoo_pilot import adjusted_returns,provider_identity,assemble_tables,metadata_snapshot,request_history,collect


class YahooPilotTests(unittest.TestCase):
    def test_full_mocked_collection_accepts_lazy_metadata_and_preserves_existing_output(self):
        dates=pd.bdate_range('2024-01-02',periods=300)
        debug=SimpleNamespace(hide_exceptions=True)
        class LazyMetadata(Mapping):
            def __init__(self,symbol):self.data={'symbol':symbol,'currency':'USD','instrumentType':'EQUITY','exchangeTimezoneName':'America/New_York'}
            def __iter__(self):return iter([*self.data,'tradingPeriods'])
            def __len__(self):return len(self.data)+1
            def __getitem__(self,key):
                if key=='tradingPeriods':raise AssertionError('Unexpected intraday fetch')
                return self.data[key]
        class Client:
            def __init__(self,symbol):self.symbol=symbol
            def history(self,**kwargs):
                if 'raise_errors' in kwargs or debug.hide_exceptions:raise AssertionError('Wrong error policy')
                prices=100+np.arange(len(dates))/100
                return pd.DataFrame({'Close':prices,'Adj Close':prices},index=dates.tz_localize('America/New_York'))
            def get_history_metadata(self,**kwargs):return LazyMetadata(self.symbol)
        yf=SimpleNamespace(Ticker=Client,config=SimpleNamespace(debug=debug))
        calendar=SimpleNamespace(get_calendar=lambda name:SimpleNamespace(sessions_in_range=lambda *args:dates))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            records=[{'ticker':f'T{i}','document_id':f'doc{i}','cik':str(i),'review_status':'passed'} for i in range(12)]
            corpus=root/'corpus.json';corpus.write_text(json.dumps(records))
            args=argparse.Namespace(corpus=str(corpus),start='2024-01-01',end='2026-11-03',output=str(root/'collection'))
            with patch.dict('sys.modules',{'yfinance':yf,'exchange_calendars':calendar}),patch('secstab.yahoo_pilot.time.sleep'),patch('secstab.yahoo_pilot.importlib.metadata.version',return_value='synthetic-fixture'),redirect_stdout(io.StringIO()):
                collect(args)
                manifest=root/'collection/manifest.json';before=manifest.read_bytes()
                result=json.loads(before)
                self.assertEqual(result['status'],'complete_data_collection_pending_review')
                self.assertEqual(result['security_count'],12)
                self.assertEqual(result['return_dates'],299)
                self.assertEqual(len(result['source_files']),24)
                with self.assertRaises(FileExistsError):collect(args)
                self.assertEqual(manifest.read_bytes(),before)
            self.assertTrue(debug.hide_exceptions)

    def test_lazy_mapping_is_preserved_without_fetching_intraday_key(self):
        data=self.metadata()
        data.update(count=np.int64(3),missing=np.nan,stamp=pd.Timestamp('2025-01-02',tz='UTC'))
        class LazyMetadata(Mapping):
            def __iter__(self):return iter([*data,'tradingPeriods'])
            def __len__(self):return len(data)+1
            def __getitem__(self,key):
                if key=='tradingPeriods':raise AssertionError('Unexpected lazy intraday fetch')
                return data[key]
        result=metadata_snapshot(LazyMetadata())
        self.assertEqual(result['symbol'],'TEST')
        self.assertEqual(result['count'],3)
        self.assertIsNone(result['missing'])
        self.assertNotIn('tradingPeriods',result)
        provider_identity(json.loads(json.dumps(result,allow_nan=False)),'TEST')

    def test_metadata_json_text_checked_and_bad_text_rejected(self):
        self.assertEqual(metadata_snapshot(json.dumps(self.metadata()))['symbol'],'TEST')
        for bad in ['not metadata','[]',None]:
            with self.assertRaises(ValueError):metadata_snapshot(bad)

    def test_modern_exception_config_is_restored_on_success_and_failure(self):
        debug=SimpleNamespace(hide_exceptions=True)
        yf=SimpleNamespace(config=SimpleNamespace(debug=debug))
        class Client:
            fail=False
            def history(self,**kwargs):
                if debug.hide_exceptions:raise AssertionError('Exceptions remained hidden')
                if 'raise_errors' in kwargs:raise AssertionError('Deprecated flag sent')
                if self.fail:raise RuntimeError('Synthetic provider failure')
                return 'result'
        client=Client()
        self.assertEqual(request_history(client,yf,'2024-01-01','2026-11-03'),'result')
        self.assertTrue(debug.hide_exceptions)
        client.fail=True
        with self.assertRaises(RuntimeError):request_history(client,yf,'2024-01-01','2026-11-03')
        self.assertTrue(debug.hide_exceptions)

    def test_older_yfinance_uses_legacy_exception_flag(self):
        captured={}
        client=SimpleNamespace(history=lambda **kwargs:captured.update(kwargs))
        request_history(client,SimpleNamespace(),'2024-01-01','2026-11-03')
        self.assertIs(captured['raise_errors'],True)

    def table(self):
        return pd.DataFrame({'Close':[100.,50.,51.],'Adj Close':[50.,50.,51.],
                             'Dividends':[0.,0.,0.],'Stock Splits':[0.,2.,0.]},
                            index=pd.date_range('2025-01-02',periods=3,tz='America/New_York'))

    def metadata(self,ticker='TEST'):
        return {'symbol':ticker,'currency':'USD','instrumentType':'EQUITY','exchangeTimezoneName':'America/New_York'}

    def dates(self):return pd.date_range('2025-01-02',periods=3)

    def test_split_does_not_create_false_half_price_return(self):
        result=adjusted_returns(self.table(),'TEST',self.dates())
        np.testing.assert_allclose(result['total_return'],[0,.02])
        self.assertTrue(result['security_id'].eq('YF:TEST').all())

    def test_dividend_not_added_twice(self):
        t=self.table();t['Close']=[100,99,100];t['Adj Close']=[99,99,100];t['Dividends']=[0,1,0]
        result=adjusted_returns(t,'TEST',self.dates())
        self.assertAlmostEqual(result['total_return'].iloc[0],0)

    def test_missing_adj_close_is_not_replaced_by_close(self):
        with self.assertRaises(ValueError):adjusted_returns(self.table().drop(columns='Adj Close'),'TEST',self.dates())

    def test_missing_and_nonpositive_prices_rejected(self):
        for value in [np.nan,0,-1]:
            t=self.table();t.loc[t.index[1],'Adj Close']=value
            with self.assertRaises(ValueError):adjusted_returns(t,'TEST',self.dates())

    def test_missing_expected_day_is_not_bridged(self):
        with self.assertRaisesRegex(ValueError,'calendar mismatch'):
            adjusted_returns(self.table().iloc[[0,2]],'TEST',self.dates())

    def test_wrong_currency_and_symbol_rejected(self):
        for bad in [{**self.metadata(),'currency':'GBP'},{**self.metadata(),'symbol':'OTHER'}]:
            with self.assertRaises(ValueError):provider_identity(bad,'TEST')

    def test_combined_panel_and_links_keep_explicit_source_order(self):
        records=[{'ticker':'B','document_id':'b','cik':'2'},{'ticker':'A','document_id':'a','cik':'1'}]
        tables={x:self.table() for x in ['A','B']};metadata={x:self.metadata(x) for x in ['A','B']}
        returns,links,summary,panel=assemble_tables(records,tables,metadata,self.dates())
        self.assertEqual(list(panel.columns),['YF:B','YF:A'])
        self.assertEqual(len(returns),4)
        self.assertTrue(links['review_status'].eq('pending_vendor_identity_review').all())


if __name__=='__main__':unittest.main()
