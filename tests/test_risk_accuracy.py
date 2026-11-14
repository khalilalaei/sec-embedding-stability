"""Synthetic subsequent-window losses and chronology checks; no market findings."""
import copy
import unittest
import numpy as np
import pandas as pd
from secstab.risk_accuracy import assumed_eligibility,evaluation_windows,evaluate_accuracy,score_level_kernel,window_losses,LOSSES


class RiskAccuracyTests(unittest.TestCase):
    def setUp(self):
        self.dates=pd.bdate_range('2026-01-02','2026-03-06')
        self.closes=pd.Series((self.dates+pd.Timedelta(hours=16)).tz_localize('America/New_York').tz_convert('UTC'),index=self.dates)
        rng=np.random.default_rng(42)
        self.panel=pd.DataFrame(rng.normal(0,.02,(len(self.dates),2)),index=self.dates,columns=['A','B'])
        self.docs=[{'document_id':'a','ticker':'A','accepted_at':'2026-01-02T22:00:00Z','source_url':'synthetic-source'}]
        self.eligibility=assumed_eligibility(self.docs,self.closes)
        self.config={'candidate_month_ends':['2026-01-31','2026-02-28'],'lookback':5,'test_days':3,'primary_runs':['a','b'],'diagnostic_runs':[],
            'primary_text_weight':.25,'supplementary_text_weights':[0,.25,1]}
        self.kernels={'a':np.eye(2),'b':np.ones((2,2))}

    def windows(self,panel=None,config=None,eligibility=None):
        return evaluation_windows(self.panel if panel is None else panel,self.closes,self.eligibility if eligibility is None else eligibility,self.config if config is None else config)

    def test_weekend_lag_and_explicit_unapproved_status(self):
        self.assertEqual(pd.Timestamp(self.eligibility[0]['assumed_eligible_from']),pd.Timestamp('2026-01-05T21:00:00Z'))
        self.assertEqual(self.eligibility[0]['review_status'],'assumption_only_not_independently_approved')
        windows,excluded=self.windows()
        self.assertFalse(excluded)
        self.assertEqual(windows[0]['decision_date'],'2026-01-30')
        self.assertEqual(windows[0]['test_start'],'2026-02-02')
        self.assertEqual(windows[0]['test_end'],'2026-02-04')

    def test_incomplete_window_logged_without_shortening(self):
        windows,excluded=self.windows(panel=self.panel.loc[:'2026-03-03'])
        self.assertEqual(len(windows),1);self.assertEqual(excluded[0]['available_subsequent_returns'],2)
        self.assertEqual(excluded[0]['reason'],'incomplete_fixed_window')
        self.assertEqual(windows[0]['test_days'],3)

    def test_late_source_excludes_earlier_candidate(self):
        docs=copy.deepcopy(self.docs);docs[0]['accepted_at']='2026-01-30T22:00:00Z'
        windows,excluded=self.windows(eligibility=assumed_eligibility(docs,self.closes))
        self.assertEqual(windows[0]['decision_date'],'2026-02-27')
        self.assertEqual(excluded[0]['reason'],'corpus_not_yet_eligible_under_assumed_lag')

    def test_realized_proxy_and_zero_weight_equivalence(self):
        windows,_=self.windows();result=evaluate_accuracy(self.panel,self.kernels,self.config,windows)
        frame=pd.DataFrame(result['window_losses'])
        for date,group in frame.groupby('decision_date'):
            baseline=group[group.run=='price_only'].iloc[0]
            for _,row in group[(group.kernel_type=='raw_cosine')&(group.text_weight==0)].iterrows():
                for loss in LOSSES:self.assertAlmostEqual(row[loss],baseline[loss],places=18)
            matrix=next(x for x in result['window_matrices'] if x['decision_date']==date)
            test=self.panel.loc[matrix['test_start']:matrix['test_end']]
            direct=float((test.to_numpy()@np.array([.5,.5])).var(ddof=1))
            self.assertAlmostEqual(baseline.realized_daily_portfolio_variance_proxy,direct,places=17)
        self.assertEqual(len(frame),18)

    def test_future_outcomes_do_not_change_corresponding_fitted_baseline(self):
        config=copy.deepcopy(self.config);config['candidate_month_ends']=['2026-01-31']
        windows,_=self.windows(config=config)
        before=evaluate_accuracy(self.panel,self.kernels,config,windows)
        changed=self.panel.copy();changed.loc['2026-02-02':'2026-02-04']*=4
        after=evaluate_accuracy(changed,self.kernels,config,windows)
        np.testing.assert_allclose(before['window_matrices'][0]['baseline_covariance'],after['window_matrices'][0]['baseline_covariance'],rtol=1e-13,atol=1e-16)
        self.assertAlmostEqual(after['window_losses'][0]['realized_daily_portfolio_variance_proxy'],16*before['window_losses'][0]['realized_daily_portfolio_variance_proxy'],places=15)

    def test_level_control_removes_structure_keeps_mean_and_psd(self):
        z=np.array([[1.,0],[0,1],[.6,.8]])
        kernel=z@z.T;control=score_level_kernel(kernel);off=~np.eye(3,dtype=bool)
        self.assertAlmostEqual(control[off].mean(),kernel[off].mean(),places=15)
        self.assertTrue(np.allclose(control[off],control[off][0]))
        self.assertGreaterEqual(np.linalg.eigvalsh(control).min(),-1e-12)
        order=[2,0,1]
        np.testing.assert_allclose(control,score_level_kernel(kernel[np.ix_(order,order)]),atol=1e-15)

    def test_loss_definition_uses_centered_variance_not_return_level(self):
        estimate=np.eye(2);realized=np.array([[2.,.5],[.5,3.]])
        losses=window_losses(estimate,realized,np.array([.5,.5]))
        self.assertAlmostEqual(losses['portfolio_variance_squared_error'],(.5-1.5)**2)
        self.assertAlmostEqual(losses['covariance_entry_mse'],(1+4+.25+.25)/4)
        self.assertAlmostEqual(losses['covariance_off_diagonal_mse'],.25)

    def test_aggregate_uses_ratio_of_mean_losses_and_counts_all_windows(self):
        windows,_=self.windows();result=evaluate_accuracy(self.panel,self.kernels,self.config,windows)
        frame=pd.DataFrame(result['window_losses']);base=frame[frame.run=='price_only']
        for row in result['aggregate_losses']:
            group=frame[(frame.run==row['run'])&(frame.kernel_type==row['kernel_type'])&(frame.text_weight==row['text_weight'])]
            self.assertEqual(row['windows'],2)
            for loss in LOSSES:
                self.assertAlmostEqual(row[loss+'_improvement_vs_price_only'],1-group[loss].mean()/base[loss].mean(),places=12)

    def test_overlapping_windows_rejected(self):
        config=copy.deepcopy(self.config);config['candidate_month_ends']=['2026-01-31','2026-01-31']
        with self.assertRaisesRegex(ValueError,'Overlapping'):self.windows(config=config)

    def test_timezone_naive_acceptance_rejected(self):
        docs=copy.deepcopy(self.docs);docs[0]['accepted_at']='2026-01-02T16:00:00'
        with self.assertRaisesRegex(ValueError,'timezone'):assumed_eligibility(docs,self.closes)


if __name__=='__main__':unittest.main()
