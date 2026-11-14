"""Synthetic calibration recovery, chronology and matched-control invariants."""
import unittest
import numpy as np
import pandas as pd
from secstab.financial import blend_covariance
from secstab.risk_accuracy import evaluate_accuracy,LOSSES
from secstab.risk_calibration import fit_calibration,correlation_from_covariance,price_constant_kernel,evaluate_calibration


class RiskCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.kernel=np.array([[1.,.7,.2],[.7,1.,.3],[.2,.3,1.]])
        corr=.35*self.kernel+.65*np.eye(3)
        self.sd=np.array([.01,.02,.04]);self.base=self.sd[:,None]*corr*self.sd[None,:]

    def test_known_scale_recovered_and_psd_diagonal_preserved(self):
        fitted,record=fit_calibration(self.base,self.kernel)
        self.assertAlmostEqual(record['alpha'],.35,places=14)
        np.testing.assert_allclose(fitted,correlation_from_covariance(self.base),atol=1e-14)
        self.assertLess(record['calibrated_target_fit_mse'],1e-25)
        self.assertGreaterEqual(np.linalg.eigvalsh(fitted).min(),0)
        blended=blend_covariance(self.base,fitted,.25)
        np.testing.assert_allclose(np.diag(blended),np.diag(self.base),atol=1e-16)

    def test_bounds_and_zero_denominator(self):
        def equi(r):return (1-r)*np.eye(3)+r*np.ones((3,3))
        self.assertEqual(fit_calibration(equi(-.2),equi(.5))[1]['alpha'],0)
        self.assertEqual(fit_calibration(equi(.9),equi(.1))[1]['alpha'],1)
        fitted,record=fit_calibration(equi(.4),np.eye(3))
        self.assertEqual(record['alpha'],0);self.assertEqual(record['denominator'],0)
        np.testing.assert_array_equal(fitted,np.eye(3))

    def test_variance_units_and_joint_permutation_do_not_change_fit(self):
        first,fit=fit_calibration(self.base,self.kernel)
        scale=np.array([3.,.5,2.]);scaled=self.base*scale[:,None]*scale[None,:]
        second,other=fit_calibration(scaled,self.kernel)
        self.assertAlmostEqual(fit['alpha'],other['alpha'],places=14)
        order=[2,0,1]
        permuted,pp=fit_calibration(self.base[np.ix_(order,order)],self.kernel[np.ix_(order,order)])
        self.assertAlmostEqual(fit['alpha'],pp['alpha'],places=14)
        np.testing.assert_allclose(permuted,first[np.ix_(order,order)],atol=1e-14)
        np.testing.assert_allclose(first,second,atol=1e-14)

    def test_calibrated_fit_no_worse_than_raw_or_identity_on_its_training_objective(self):
        rng=np.random.default_rng(41)
        for _ in range(10):
            z=rng.normal(size=(5,8));z/=np.linalg.norm(z,axis=1,keepdims=True)
            a=rng.normal(size=(5,8));cov=a@a.T
            _,fit=fit_calibration(cov,z@z.T)
            r=correlation_from_covariance(cov);off=np.triu_indices(5,1)
            self.assertLessEqual(fit['calibrated_target_fit_mse'],fit['raw_target_fit_mse']+1e-14)
            self.assertLessEqual(fit['calibrated_target_fit_mse'],float(np.mean(r[off]**2))+1e-14)

    def test_level_fit_matches_past_price_constant_control_when_unclipped(self):
        target=.8*np.eye(3)+.2*np.ones((3,3))
        kernel=.2*np.eye(3)+.8*np.ones((3,3))
        fitted,record=fit_calibration(target,kernel);constant,rho=price_constant_kernel(target)
        self.assertAlmostEqual(record['alpha'],.25,places=14);self.assertAlmostEqual(rho,.2,places=14)
        np.testing.assert_allclose(fitted,constant,atol=1e-14)

    def test_covariance_decomposition_exposes_extra_diagonal_shrinkage(self):
        target,fit=fit_calibration(self.base,self.kernel);alpha=fit['alpha']
        actual=blend_covariance(self.base,target,.25)
        independent=.75*self.base+.25*(1-alpha)*np.diag(np.diag(self.base))+.25*alpha*self.sd[:,None]*self.kernel*self.sd[None,:]
        np.testing.assert_allclose(actual,independent,atol=1e-16)

    def fixture(self):
        rng=np.random.default_rng(7)
        panel=pd.DataFrame(rng.normal(0,.01,(40,3)),index=pd.bdate_range('2026-01-02',periods=40),columns=['A','B','C'])
        config={'lookback':20,'test_days':5,'primary_text_weight':.25,'primary_runs':['a'],'diagnostic_runs':[],'supplementary_text_weights':[.25]}
        windows=[{'decision_date':str(panel.index[24].date())}]
        return panel,config,windows

    def test_future_labels_do_not_affect_coefficients_or_corresponding_estimates(self):
        panel,config,windows=self.fixture()
        before=evaluate_calibration(panel,{'a':self.kernel},config,windows)
        changed=panel.copy();changed.iloc[25:30]*=4
        after=evaluate_calibration(changed,{'a':self.kernel},config,windows)
        self.assertEqual(before['calibration_fits'],after['calibration_fits'])
        for a,b in zip(before['window_losses'],after['window_losses']):
            self.assertAlmostEqual(a['estimated_daily_portfolio_variance'],b['estimated_daily_portfolio_variance'],places=16)
            self.assertAlmostEqual(b['realized_daily_portfolio_variance_proxy'],16*a['realized_daily_portfolio_variance_proxy'],places=15)

    def test_legacy_raw_and_baseline_losses_unchanged(self):
        panel,config,windows=self.fixture()
        current=evaluate_calibration(panel,{'a':self.kernel},config,windows)
        legacy=evaluate_accuracy(panel,{'a':self.kernel},config,windows)
        for old in legacy['window_losses']:
            if old['kernel_type'] not in ['raw_cosine','price_only']:continue
            new=next(r for r in current['window_losses'] if r['run']==old['run'] and r['kind']==old['kernel_type'])
            for loss in LOSSES:self.assertAlmostEqual(old[loss],new[loss],places=20)
        self.assertEqual(len(current['window_losses']),6)
        self.assertEqual(len(current['calibration_fits']),2)

    def test_invalid_kernel_or_variance_rejected(self):
        with self.assertRaisesRegex(ValueError,'Dimension'):fit_calibration(self.base,np.eye(2))
        with self.assertRaisesRegex(ValueError,'positive marginal'):fit_calibration(np.zeros((3,3)),self.kernel)
        with self.assertRaisesRegex(ValueError,'positive semidefinite'):fit_calibration(self.base,np.array([[1,2,0],[2,1,0],[0,0,1]]))


if __name__=='__main__':unittest.main()
