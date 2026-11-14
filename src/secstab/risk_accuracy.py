"""Exploratory retrospective subsequent-window risk losses, not trading evidence."""
import numpy as np
import pandas as pd
from .financial import split_window,price_covariance,blend_covariance,portfolio_variance,covariance_mse,checked_psd

LOSSES=['portfolio_variance_squared_error','covariance_entry_mse','covariance_off_diagonal_mse']


def assumed_eligibility(documents,closes):
    """Explicit assumption-only records; never manufacture approved eligibility."""
    if not isinstance(closes.index,pd.DatetimeIndex) or closes.index.tz is not None or closes.index.has_duplicates or not closes.index.is_monotonic_increasing:
        raise ValueError('Need ordered unique session labels')
    if not documents or len({d['document_id'] for d in documents})!=len(documents):raise ValueError('Duplicate/empty documents')
    result=[]
    for d in documents:
        accepted=pd.Timestamp(d['accepted_at'])
        if accepted.tz is None:raise ValueError('Acceptance requires timezone')
        local_date=accepted.tz_convert('America/New_York').tz_localize(None).normalize()
        later=closes.loc[closes.index>local_date]
        if later.empty:raise ValueError('Calendar does not cover assumed eligibility')
        eligible=pd.Timestamp(later.iloc[0])
        if eligible.tz is None or eligible<=accepted:raise ValueError('Invalid assumed close')
        result.append({'document_id':d['document_id'],'ticker':d['ticker'],'accepted_at':accepted.isoformat(),
            'assumed_eligible_from':eligible.isoformat(),'source_url':d['source_url'],
            'review_status':'assumption_only_not_independently_approved',
            'rule':'first XNYS session close strictly after acceptance local date'})
    return result


def score_level_kernel(kernel):
    kernel=checked_psd(kernel,unit_diagonal=True);n=len(kernel)
    c=float(kernel[~np.eye(n,dtype=bool)].mean())
    return checked_psd((1-c)*np.eye(n)+c*np.ones((n,n)),unit_diagonal=True)


def evaluation_windows(panel,closes,eligibility,config):
    if not eligibility:raise ValueError('Missing assumption records')
    last_eligible=max(pd.Timestamp(d['assumed_eligible_from']) for d in eligibility)
    windows=[];exclusions=[];last_test_end=None
    for candidate in config['candidate_month_ends']:
        month_end=pd.Timestamp(candidate)
        if month_end.tz is not None or month_end!=month_end.normalize() or month_end!=month_end+pd.offsets.MonthEnd(0):
            raise ValueError('Candidate must be a naive calendar month end')
        sessions=closes.index[(closes.index.to_period('M')==month_end.to_period('M'))&(closes.index<=month_end)]
        if len(sessions)==0:raise ValueError('Calendar does not cover candidate month')
        decision=sessions[-1];close=pd.Timestamp(closes.loc[decision])
        if close.tz is None or last_eligible.tz is None:raise ValueError('Timing requires aware closes/assumptions')
        available_train=int((panel.index<=decision).sum());available_test=int((panel.index>decision).sum())
        entry={'candidate_month_end':candidate,'decision_date':str(decision.date()),'decision_close':close.isoformat()}
        if last_eligible>close:
            exclusions.append({**entry,'reason':'corpus_not_yet_eligible_under_assumed_lag'});continue
        if decision not in panel.index or available_train<config['lookback'] or available_test<config['test_days']:
            exclusions.append({**entry,'reason':'incomplete_fixed_window','available_trailing_returns':available_train,
                'available_subsequent_returns':available_test});continue
        train,test=split_window(panel,decision,config['lookback'],config['test_days'])
        if last_test_end is not None and test.index[0]<=last_test_end:raise ValueError('Overlapping evaluation windows')
        if windows and decision<=pd.Timestamp(windows[-1]['decision_date']):raise ValueError('Candidates must increase')
        entry.update(train_start=str(train.index[0].date()),train_end=str(train.index[-1].date()),
            test_start=str(test.index[0].date()),test_end=str(test.index[-1].date()),train_days=len(train),test_days=len(test))
        windows.append(entry);last_test_end=test.index[-1]
    if not windows:raise ValueError('No complete assumed-eligible windows')
    return windows,exclusions


def window_losses(estimate,realized,weights):
    estimated=portfolio_variance(estimate,weights);observed=portfolio_variance(realized,weights)
    off=~np.eye(len(weights),dtype=bool)
    return {'estimated_daily_portfolio_variance':estimated,'realized_daily_portfolio_variance_proxy':observed,
        'portfolio_variance_squared_error':(estimated-observed)**2,
        'covariance_entry_mse':covariance_mse(estimate,realized),
        'covariance_off_diagonal_mse':float(np.mean((estimate[off]-realized[off])**2))}


def evaluate_accuracy(panel,kernels,config,windows):
    names=config['primary_runs']+config['diagnostic_runs']
    if len(set(names))!=len(names) or set(names)!=set(kernels):raise ValueError('Kernel/config identity mismatch')
    if len(set(config['supplementary_text_weights']))!=len(config['supplementary_text_weights']) or config['primary_text_weight'] not in config['supplementary_text_weights']:
        raise ValueError('Primary text weight must appear in unique fixed grid')
    if panel.columns.has_duplicates:raise ValueError('Duplicate securities')
    for kernel in kernels.values():
        if checked_psd(kernel,unit_diagonal=True).shape!=(panel.shape[1],panel.shape[1]):raise ValueError('Kernel dimension mismatch')
    w=np.full(panel.shape[1],1/panel.shape[1]);rows=[];matrices=[]
    last_end=None
    for window in windows:
        train,test=split_window(panel,window['decision_date'],config['lookback'],config['test_days'])
        if last_end is not None and test.index[0]<=last_end:raise ValueError('Overlapping evaluation windows')
        last_end=test.index[-1]
        base=price_covariance(train)
        realized=checked_psd(np.cov(test.to_numpy(float),rowvar=False,ddof=1))
        # Independent scalar calculation checks the realized proxy/weight ordering.
        direct=float((test.to_numpy(float)@w).var(ddof=1))
        if not np.isclose(portfolio_variance(realized,w),direct,rtol=1e-12,atol=1e-16):raise ValueError('Realized portfolio proxy mismatch')
        entry={'decision_date':window['decision_date'],'test_start':str(test.index[0].date()),'test_end':str(test.index[-1].date())}
        rows.append({**entry,'run':'price_only','kernel_type':'price_only','text_weight':0.,'arm_role':'baseline',**window_losses(base,realized,w)})
        matrices.append({**entry,'security_order':list(panel.columns),'baseline_covariance':base.tolist(),'realized_covariance_proxy':realized.tolist()})
        for name in names:
            for kind,grid in [('raw_cosine',config['supplementary_text_weights']),('score_level_control',[config['primary_text_weight']])]:
                kernel=kernels[name] if kind=='raw_cosine' else score_level_kernel(kernels[name])
                for weight in grid:
                    estimate=blend_covariance(base,kernel,weight)
                    if not np.allclose(np.diag(estimate),np.diag(base),rtol=1e-12,atol=1e-16):raise ValueError('Marginal variances changed')
                    rows.append({**entry,'run':name,'kernel_type':kind,'text_weight':weight,
                        'arm_role':'primary' if name in config['primary_runs'] else 'environment_diagnostic',**window_losses(estimate,realized,w)})
    frame=pd.DataFrame(rows);base_rows=frame[frame.run=='price_only'].set_index('decision_date')
    if len(base_rows)!=len(windows) or base_rows.index.has_duplicates:raise ValueError('Invalid baseline grouping')
    aggregates=[]
    for (name,kind,weight),group in frame.groupby(['run','kernel_type','text_weight'],sort=False):
        if len(group)!=len(windows) or group.decision_date.duplicated().any():raise ValueError('Incomplete estimator window group')
        summary={'run':name,'kernel_type':kind,'text_weight':float(weight),'arm_role':group.arm_role.iloc[0],'windows':len(group)}
        for loss in LOSSES:
            value=float(group[loss].mean());baseline=float(base_rows[loss].mean())
            summary['mean_'+loss]=value
            summary[loss+'_improvement_vs_price_only']=1-value/baseline if baseline>0 else None
            summary[loss+'_windows_better_than_price_only']=int(sum(row[loss]<base_rows.loc[row['decision_date'],loss] for row in group.to_dict('records')))
        aggregates.append(summary)
    return {'window_losses':rows,'aggregate_losses':aggregates,'window_matrices':matrices}
