"""Fixed-price, fixed-weight mechanical covariance sensitivity, not a backtest."""
import numpy as np
import pandas as pd
from .financial import price_covariance,blend_covariance,portfolio_variance,checked_psd


def compute_snapshot(panel,kernels,config):
    """Return aggregate metrics and matrices; accepts no future outcome window."""
    if not isinstance(panel.index,pd.DatetimeIndex) or panel.index.has_duplicates or not panel.index.is_monotonic_increasing:
        raise ValueError('Need unique increasing daily return dates')
    if panel.index.tz is not None or not panel.index.equals(panel.index.normalize()):raise ValueError('Need naive daily date labels')
    if panel.columns.has_duplicates or panel.shape[1]<2:raise ValueError('Need unique ordered securities')
    if not np.isfinite(panel.to_numpy(float)).all():raise ValueError('Nonfinite returns')
    asof=pd.Timestamp(config['asof_date'])
    if asof not in panel.index:raise ValueError('Snapshot date missing')
    lookback=config['lookback'];annual=config['annualization_sessions']
    if not isinstance(lookback,int) or lookback<2 or not isinstance(annual,int) or annual<1:raise ValueError('Invalid window/annualization')
    history=panel.loc[:asof].tail(lookback)
    if len(history)!=lookback:raise ValueError('Insufficient trailing data')
    names=config['primary_runs']+config['diagnostic_runs']
    if len(set(names))!=len(names) or set(names)!=set(kernels):raise ValueError('Kernel/config identity mismatch')
    base=price_covariance(history)
    w=np.full(panel.shape[1],1/panel.shape[1]);pv=portfolio_variance(base,w)
    if pv<=0:raise ValueError('Degenerate baseline portfolio')
    primary=float(config['primary_text_weight']);grid=config['supplementary_text_weights']
    if primary not in grid or len(set(grid))!=len(grid):raise ValueError('Primary text weight must be in unique fixed grid')
    rows=[];matrices={};off=~np.eye(len(w),dtype=bool)
    for name in names:
        kernel=checked_psd(kernels[name],unit_diagonal=True)
        if kernel.shape!=base.shape:raise ValueError('Kernel/security dimension mismatch')
        for weight in grid:
            cov=blend_covariance(base,kernel,weight)
            if not np.allclose(np.diag(cov),np.diag(base),rtol=1e-12,atol=1e-16):raise ValueError('Marginal variances changed')
            variance=portfolio_variance(cov,w)
            rows.append({'run':name,'arm_role':'primary' if name in config['primary_runs'] else 'environment_diagnostic',
                'text_weight':weight,'daily_portfolio_variance':variance,
                'annualized_portfolio_sd':float(np.sqrt(annual*variance)),
                'variance_change_relative_to_price_baseline':variance/pv-1,
                'covariance_frobenius_change_relative_to_price_baseline':float(np.linalg.norm(cov-base)/np.linalg.norm(base)),
                'mean_off_diagonal_kernel_cosine':float(kernel[off].mean()),
                'max_absolute_marginal_variance_change':float(np.max(np.abs(np.diag(cov)-np.diag(base))))})
            if weight==primary:matrices[name]=cov
    comparisons=[]
    for a,b in config['contrasts']:
        ca,cb=matrices[a],matrices[b]
        va,vb=portfolio_variance(ca,w),portfolio_variance(cb,w)
        comparisons.append({'run_a':a,'run_b':b,'text_weight':primary,
            'variance_b_minus_a_relative_to_price_baseline':(vb-va)/pv,
            'variance_b_relative_to_a_minus_one':vb/va-1,
            'annualized_sd_b_minus_a_percentage_points':100*(np.sqrt(annual*vb)-np.sqrt(annual*va)),
            'covariance_frobenius_distance_relative_to_price_baseline':float(np.linalg.norm(cb-ca)/np.linalg.norm(base))})
    primary_values=[portfolio_variance(matrices[n],w) for n in config['primary_runs']]
    neural_values=[portfolio_variance(matrices[n],w) for n in config['primary_runs'] if n!='pilot_tfidf']
    summary={'scope':config['scope'],'asof_date':str(asof.date()),'trailing_first_date':str(history.index[0].date()),
        'trailing_last_date':str(history.index[-1].date()),'trailing_observations':len(history),'securities':len(w),
        'weights':w.tolist(),'annualization_sessions':annual,'primary_text_weight':primary,
        'baseline_daily_portfolio_variance':pv,'baseline_annualized_portfolio_sd':float(np.sqrt(annual*pv)),
        'primary_variance_range_relative_to_price_baseline':(max(primary_values)-min(primary_values))/pv,
        'neural_variance_range_relative_to_price_baseline':(max(neural_values)-min(neural_values))/pv if neural_values else None,
        'no_outcome_evaluation':True}
    stats=[{'security_id':str(s),'trailing_mean_daily_proxy_return':float(history[s].mean()),
        'baseline_annualized_marginal_sd':float(np.sqrt(annual*base[i,i]))} for i,s in enumerate(panel.columns)]
    return {'summary':summary,'settings':rows,'contrasts':comparisons,'stock_descriptives':stats,
        'matrices':{'security_order':[str(x) for x in panel.columns],'baseline':base.tolist(),
            'primary_text_weight_covariances':{k:v.tolist() for k,v in matrices.items()}}}
