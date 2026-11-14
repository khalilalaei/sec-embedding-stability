"""Structural checks for the mechanical risk experiment; synthetic returns only."""
import copy
import unittest
import numpy as np
import pandas as pd
from secstab.risk_snapshot import compute_snapshot


class RiskSnapshotTests(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(102)
        self.panel=pd.DataFrame(rng.normal(0,.01,(30,3)),index=pd.bdate_range('2026-01-02',periods=30),columns=['A','B','C'])
        self.config={'scope':'synthetic','asof_date':str(self.panel.index[24].date()),'lookback':20,'annualization_sessions':252,
            'primary_text_weight':.25,'supplementary_text_weights':[0,.25,1],
            'primary_runs':['a','b'],'diagnostic_runs':[],'contrasts':[['a','b']]}
        self.kernels={'a':np.eye(3),'b':np.ones((3,3))}

    def compute(self,panel=None,kernels=None,config=None):
        return compute_snapshot(self.panel if panel is None else panel,self.kernels if kernels is None else kernels,self.config if config is None else config)

    def test_zero_weight_is_baseline_and_marginal_variance_stays_fixed(self):
        result=self.compute();base=np.array(result['matrices']['baseline'])
        for row in result['settings']:
            if row['text_weight']==0:
                self.assertAlmostEqual(row['variance_change_relative_to_price_baseline'],0,places=14)
            self.assertLess(row['max_absolute_marginal_variance_change'],1e-15)
        for cov in result['matrices']['primary_text_weight_covariances'].values():
            np.testing.assert_allclose(np.diag(cov),np.diag(base),rtol=1e-13,atol=1e-16)

    def test_future_observations_cannot_change_snapshot(self):
        before=self.compute();panel=self.panel.copy();panel.iloc[25:]=1e6
        after=self.compute(panel=panel)
        self.assertEqual(before['summary']['trailing_first_date'],after['summary']['trailing_first_date'])
        np.testing.assert_allclose(before['matrices']['baseline'],after['matrices']['baseline'],rtol=1e-13,atol=1e-16)
        for a,b in zip(before['settings'],after['settings']):
            for key in ['daily_portfolio_variance','annualized_portfolio_sd','variance_change_relative_to_price_baseline']:
                self.assertAlmostEqual(a[key],b[key],places=12)

    def test_joint_security_permutation_preserves_equal_weight_risk(self):
        before=self.compute();order=[2,0,1]
        kernels={k:v[np.ix_(order,order)] for k,v in self.kernels.items()}
        after=self.compute(panel=self.panel.iloc[:,order],kernels=kernels)
        for a,b in zip(before['settings'],after['settings']):
            self.assertAlmostEqual(a['daily_portfolio_variance'],b['daily_portfolio_variance'],places=15)

    def test_fixed_blend_contrast_matches_direct_portfolio_quadratic_form(self):
        result=self.compute();base=np.array(result['matrices']['baseline']);sd=np.sqrt(np.diag(base))
        # All-ones versus identity target changes only off-diagonal entries.
        expected=.25*(sd.sum()**2-(sd**2).sum())/9
        observed=result['contrasts'][0]['variance_b_minus_a_relative_to_price_baseline']*result['summary']['baseline_daily_portfolio_variance']
        self.assertAlmostEqual(observed,expected,places=15)

    def test_invalid_inputs_rejected(self):
        config=copy.deepcopy(self.config);config['lookback']=100
        with self.assertRaisesRegex(ValueError,'Insufficient'):self.compute(config=config)
        panel=self.panel.copy();panel.columns=['A','A','C']
        with self.assertRaisesRegex(ValueError,'unique ordered'):self.compute(panel=panel)
        kernels=dict(self.kernels);kernels['a']=np.array([[1,2,0],[2,1,0],[0,0,1]])
        with self.assertRaisesRegex(ValueError,'positive semidefinite'):self.compute(kernels=kernels)
        with self.assertRaisesRegex(ValueError,'identity mismatch'):self.compute(kernels={'a':np.eye(3)})


if __name__=='__main__':unittest.main()
