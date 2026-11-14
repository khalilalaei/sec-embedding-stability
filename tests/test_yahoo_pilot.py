"""Synthetic provider fixtures only; no live Yahoo requests or market findings."""
import unittest
import numpy as np
import pandas as pd
from secstab.yahoo_pilot import adjusted_returns,provider_identity,assemble_tables


class YahooPilotTests(unittest.TestCase):
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
