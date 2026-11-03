"""Synthetic financial-method tests. No market observations or research findings."""
import unittest
import numpy as np
import pandas as pd
from secstab.financial import (validate_returns,align_returns,split_window,check_filing_eligibility,
    checked_psd,price_covariance,blend_covariance,portfolio_variance,covariance_mse)


class FinancialTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame({'date':['2025-01-02','2025-01-02','2025-01-03','2025-01-03'],
                             'security_id':['A','B','A','B'],'total_return':[.01,.02,-.01,.03]})

    def test_duplicates_missing_and_sentinel_returns_rejected(self):
        f=self.frame()
        for invalid in [pd.concat([f,f.iloc[:1]]),f.assign(total_return=[.01,np.nan,.01,.01]),f.assign(total_return=[.01,-66,.01,.01])]:
            with self.assertRaises(ValueError):validate_returns(invalid)
        # A valid complete loss is distinct from a missing/source code.
        self.assertEqual(validate_returns(f.assign(total_return=[-1,.02,-.01,.03])).iloc[0]['total_return'],-1)

    def test_panel_order_matches_explicit_security_order(self):
        p=align_returns(self.frame(),['B','A'],pd.to_datetime(['2025-01-02','2025-01-03']))
        self.assertEqual(list(p.columns),['B','A'])
        np.testing.assert_allclose(p.iloc[0],[.02,.01])

    def test_missing_whole_trading_date_is_not_silently_dropped(self):
        with self.assertRaisesRegex(ValueError,'Missing expected'):
            align_returns(self.frame(),['A','B'],pd.to_datetime(['2025-01-02','2025-01-03','2025-01-06']))

    def test_past_future_windows_are_disjoint_and_baseline_ignores_future(self):
        p=pd.DataFrame(np.arange(12).reshape(6,2)/100,index=pd.date_range('2025-01-01',periods=6))
        train,test=split_window(p,'2025-01-03',3,2)
        self.assertEqual(train.index.max(),pd.Timestamp('2025-01-03'))
        self.assertEqual(test.index.min(),pd.Timestamp('2025-01-04'))
        changed=p.copy();changed.loc[changed.index>'2025-01-03']+=.5
        new_train,_=split_window(changed,'2025-01-03',3,2)
        np.testing.assert_array_equal(price_covariance(train),price_covariance(new_train))

    def test_filing_timing_requires_review_timezone_and_eligibility(self):
        record={'document_id':'doc','eligible_from':'2025-01-03T21:00:00Z','review_status':'passed'}
        self.assertTrue(check_filing_eligibility(['doc'],[record],'2025-01-03T21:00:00Z'))
        for decision in ['2025-01-02T21:00:00Z','2025-01-03']:
            with self.assertRaises(ValueError):check_filing_eligibility(['doc'],[record],decision)
        with self.assertRaises(ValueError):check_filing_eligibility(['doc'],[{**record,'review_status':'pending'}],'2025-01-04T21:00:00Z')

    def test_indefinite_text_kernel_rejected(self):
        with self.assertRaisesRegex(ValueError,'positive semidefinite'):
            checked_psd([[1,.9,.9],[.9,1,-.9],[.9,-.9,1]],unit_diagonal=True)

    def test_text_blend_preserves_marginal_variance_and_psd(self):
        base=np.array([[.04,.01],[.01,.09]])
        kernel=np.array([[1,.5],[.5,1]])
        mixed=blend_covariance(base,kernel,.25)
        np.testing.assert_allclose(np.diag(mixed),[.04,.09])
        self.assertAlmostEqual(mixed[0,1],.75*.01+.25*.03)
        self.assertGreaterEqual(np.linalg.eigvalsh(mixed).min(),0)
        np.testing.assert_array_equal(blend_covariance(base,kernel,0),base)
        self.assertAlmostEqual(blend_covariance(base,kernel,1)[0,1],.03)
        with self.assertRaises(ValueError):blend_covariance(base,kernel,1.1)

    def test_portfolio_variance_has_hand_calculated_value(self):
        self.assertAlmostEqual(portfolio_variance([[.04,.01],[.01,.09]],[.5,.5]),.0375)
        with self.assertRaises(ValueError):portfolio_variance(np.eye(2),[1,1])

    def test_covariance_error_is_mean_squared_entry_error(self):
        a=np.eye(2);b=np.diag([2.,1.])
        self.assertAlmostEqual(covariance_mse(a,b),.25)


if __name__=='__main__':unittest.main()
