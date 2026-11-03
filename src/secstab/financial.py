"""Financial-pilot numerical foundations. No downloads, forecasts or backtests.

Canonical returns must be documented daily decimal TOTAL returns. Source-specific
CRSP conversion and security links are deliberately not inferred by this module.
"""
import argparse
import json
import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf


def validate_returns(frame):
    needed={'date','security_id','total_return'}
    if not needed.issubset(frame.columns):
        raise ValueError('Required columns: date, security_id, total_return')
    result=frame.loc[:,['date','security_id','total_return']].copy()
    if result.empty or result.isna().any().any():
        raise ValueError('Empty/missing return data; never fill missing returns with zero')
    result['security_id']=result['security_id'].astype(str).str.strip()
    if result['security_id'].eq('').any():raise ValueError('Empty security identifier')
    result['date']=pd.to_datetime(result['date'],errors='raise')
    if result['date'].dt.tz is not None or not result['date'].eq(result['date'].dt.normalize()).all():
        raise ValueError('Return date must be a timezone-free trading-date label at midnight')
    result['total_return']=pd.to_numeric(result['total_return'],errors='raise')
    if not np.isfinite(result['total_return']).all() or (result['total_return'] < -1).any():
        raise ValueError('Invalid decimal total return; quarantine missing/source sentinel codes')
    if result.duplicated(['date','security_id']).any():
        raise ValueError('Duplicate security-date observation')
    return result.sort_values(['date','security_id']).reset_index(drop=True)


def align_returns(frame,security_ids,expected_dates):
    """Require an externally specified trading calendar; never silently intersect."""
    checked=validate_returns(frame)
    ids=[str(x) for x in security_ids]
    dates=pd.DatetimeIndex(expected_dates)
    if len(ids)<2 or len(set(ids))!=len(ids):raise ValueError('Need unique ordered security IDs')
    if len(dates)<2 or dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError('Expected trading dates must be unique and increasing')
    if dates.tz is not None or not dates.equals(dates.normalize()):
        raise ValueError('Expected dates must be timezone-free trading-date labels')
    panel=checked.pivot(index='date',columns='security_id',values='total_return').reindex(index=dates,columns=ids)
    if panel.isna().any().any():
        raise ValueError('Missing expected security-date return; resolve or log an exclusion, never impute')
    return panel


def split_window(panel,decision_date,train_days=252,test_days=21):
    if not isinstance(panel.index,pd.DatetimeIndex) or panel.index.has_duplicates or not panel.index.is_monotonic_increasing:
        raise ValueError('Return panel must have a unique increasing DatetimeIndex')
    if panel.index.tz is not None or not panel.index.equals(panel.index.normalize()):
        raise ValueError('Panel index must contain timezone-free trading dates')
    if train_days<2 or test_days<2:raise ValueError('Need at least two training and evaluation dates')
    decision=pd.Timestamp(decision_date)
    if decision.tz is not None or decision!=decision.normalize():raise ValueError('Use a trading-date label')
    if decision not in panel.index:raise ValueError('Decision close is not an admitted trading date')
    if not np.isfinite(panel.to_numpy(dtype=float)).all():raise ValueError('Panel contains invalid returns')
    train=panel.loc[panel.index<=decision].tail(train_days)
    test=panel.loc[panel.index>decision].head(test_days)
    if len(train)!=train_days or len(test)!=test_days:raise ValueError('Insufficient trailing/evaluation data')
    return train.copy(),test.copy()


def check_filing_eligibility(document_ids,availability,decision_time):
    """Availability must be independently reviewed; acceptance date alone is not enough."""
    decision=pd.Timestamp(decision_time)
    if decision.tz is None:raise ValueError('Decision timestamp requires an explicit timezone')
    if len(availability)!=len(document_ids):raise ValueError('Need one availability record per document')
    lookup={r['document_id']:r for r in availability}
    if len(lookup)!=len(availability) or set(lookup)!=set(document_ids):
        raise ValueError('Availability identities do not match ordered documents')
    for doc in document_ids:
        record=lookup[doc]
        if record.get('review_status')!='passed':raise ValueError('Filing availability has not been reviewed')
        eligible=pd.Timestamp(record['eligible_from'])
        if eligible.tz is None:raise ValueError('Filing eligibility requires an explicit timezone')
        if eligible>decision:raise ValueError('Filing was not eligible at the decision time: '+doc)
    return True


def checked_psd(matrix,unit_diagonal=False):
    matrix=np.asarray(matrix,dtype=float)
    if matrix.ndim!=2 or matrix.shape[0]!=matrix.shape[1] or len(matrix)<2 or not np.isfinite(matrix).all():
        raise ValueError('Expected a finite square matrix')
    if not np.allclose(matrix,matrix.T,rtol=0,atol=1e-12):raise ValueError('Matrix must be symmetric')
    scale=max(float(np.max(np.abs(matrix))),np.finfo(float).tiny)
    if np.linalg.eigvalsh(matrix).min() < -1e-10*scale:
        raise ValueError('Matrix is not positive semidefinite; do not silently repair it')
    if unit_diagonal and not np.allclose(np.diag(matrix),1,rtol=0,atol=1e-10):
        raise ValueError('Text kernel must have unit diagonal')
    return matrix


def price_covariance(trailing_returns):
    x=np.asarray(trailing_returns,dtype=float)
    if x.ndim!=2 or min(x.shape)<2 or not np.isfinite(x).all():raise ValueError('Invalid trailing returns')
    result=LedoitWolf(assume_centered=False).fit(x).covariance_
    checked_psd(result)
    if np.any(np.diag(result)<=0):raise ValueError('Nonpositive baseline variance')
    return result


def blend_covariance(baseline,text_kernel,text_weight):
    """Hold baseline marginal variances fixed; change only dependence structure."""
    base=checked_psd(baseline)
    kernel=checked_psd(text_kernel,unit_diagonal=True)
    if base.shape!=kernel.shape:raise ValueError('Covariance/kernel shape mismatch')
    if not np.isfinite(text_weight) or not 0<=text_weight<=1:raise ValueError('Text weight must lie in [0,1]')
    if np.any(np.diag(base)<=0):raise ValueError('Nonpositive baseline variance')
    volatility=np.sqrt(np.diag(base))
    target=volatility[:,None]*kernel*volatility[None,:]
    result=(1-text_weight)*base+text_weight*target
    return checked_psd(result)


def portfolio_variance(covariance,weights):
    cov=checked_psd(covariance)
    weights=np.asarray(weights,dtype=float)
    if weights.shape!=(len(cov),) or not np.isfinite(weights).all() or np.any(weights<0) or not np.isclose(weights.sum(),1):
        raise ValueError('Expected finite long-only, fully invested portfolio weights')
    return float(weights@cov@weights)


def covariance_mse(estimate,realized_proxy):
    estimate=checked_psd(estimate);observed=checked_psd(realized_proxy)
    if estimate.shape!=observed.shape:raise ValueError('Covariance shapes differ')
    return float(np.mean((estimate-observed)**2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check-returns',required=True,help='Canonical CSV; this is a format check, not a backtest')
    args=p.parse_args()
    frame=validate_returns(pd.read_csv(args.check_returns,dtype={'security_id':'string'}))
    print(json.dumps({'status':'return_format_passed','observations':len(frame),'securities':frame['security_id'].nunique(),
                     'first_date':str(frame['date'].min().date()),'last_date':str(frame['date'].max().date()),
                     'scope':'Format only: source return definition, links, calendar and document/model timing still require review'},indent=2))


if __name__=='__main__':main()
