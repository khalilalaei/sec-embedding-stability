"""Past-price-only shrinkage calibration, retaining text-free comparison arms."""
import numpy as np
import pandas as pd
from .financial import checked_psd,price_covariance,blend_covariance,split_window
from .risk_accuracy import score_level_kernel,window_losses,LOSSES


def correlation_from_covariance(covariance):
    covariance=checked_psd(covariance)
    if np.any(np.diag(covariance)<=0):raise ValueError('Need positive marginal variances')
    sd=np.sqrt(np.diag(covariance))
    return checked_psd(covariance/sd[:,None]/sd[None,:],unit_diagonal=True)


def fit_calibration(trailing_covariance,kernel):
    """Fit one coefficient to trailing correlations. Accepts no future labels."""
    target=correlation_from_covariance(trailing_covariance)
    kernel=checked_psd(kernel,unit_diagonal=True)
    if kernel.shape!=target.shape:raise ValueError('Dimension mismatch')
    upper=np.triu_indices(len(kernel),1);x=kernel[upper];y=target[upper]
    denominator=float(x@x);numerator=float(x@y)
    unconstrained=numerator/denominator if denominator>0 else 0.
    alpha=float(np.clip(unconstrained,0,1))
    calibrated=checked_psd((1-alpha)*np.eye(len(kernel))+alpha*kernel,unit_diagonal=True)
    return calibrated,{'alpha':alpha,'unconstrained_alpha':unconstrained,'fit_pair_count':len(x),
        'numerator':numerator,'denominator':denominator,
        'raw_target_fit_mse':float(np.mean((x-y)**2)),
        'calibrated_target_fit_mse':float(np.mean((calibrated[upper]-y)**2))}


def price_constant_kernel(trailing_covariance):
    correlation=correlation_from_covariance(trailing_covariance);n=len(correlation)
    rho=float(correlation[np.triu_indices(n,1)].mean())
    rho=float(np.clip(rho,-1/(n-1),1))
    return checked_psd((1-rho)*np.eye(n)+rho*np.ones((n,n)),unit_diagonal=True),rho


def evaluate_calibration(panel,kernels,config,windows):
    names=config['primary_runs']+config['diagnostic_runs']
    if len(names)!=len(set(names)) or set(names)!=set(kernels):raise ValueError('Kernel/config identity mismatch')
    if panel.columns.has_duplicates or panel.shape[1]<2:raise ValueError('Need unique ordered securities')
    for kernel in kernels.values():
        if checked_psd(kernel,unit_diagonal=True).shape!=(panel.shape[1],panel.shape[1]):raise ValueError('Kernel dimension mismatch')
    weight=config['primary_text_weight'];w=np.full(panel.shape[1],1/panel.shape[1])
    rows=[];fits=[];last_end=None
    for window in windows:
        train,test=split_window(panel,window['decision_date'],config['lookback'],config['test_days'])
        if last_end is not None and test.index[0]<=last_end:raise ValueError('Overlapping evaluation windows')
        last_end=test.index[-1]
        base=price_covariance(train)
        constant,rho=price_constant_kernel(base)
        # All targets and fitted coefficients are built before constructing labels.
        targets=[]
        for name in names:
            full,full_fit=fit_calibration(base,kernels[name])
            level,level_fit=fit_calibration(base,score_level_kernel(kernels[name]))
            role='primary' if name in config['primary_runs'] else 'environment_diagnostic'
            targets.extend([(name,'raw_cosine',role,kernels[name]),(name,'calibrated_cosine',role,full),(name,'calibrated_level_control',role,level)])
            for kind,fit in [('calibrated_cosine',full_fit),('calibrated_level_control',level_fit)]:
                fits.append({'decision_date':window['decision_date'],'fit_start':str(train.index[0].date()),'fit_end':str(train.index[-1].date()),
                    'run':name,'kind':kind,'arm_role':role,**fit})
        estimates=[('price_only','price_only','baseline',base,0.),
            ('diagonal_target','diagonal_target','price_control',blend_covariance(base,np.eye(len(w)),weight),weight),
            ('price_constant_correlation','price_constant_correlation','price_control',blend_covariance(base,constant,weight),weight)]
        estimates.extend((name,kind,role,blend_covariance(base,kernel,weight),weight) for name,kind,role,kernel in targets)
        realized=checked_psd(np.cov(test.to_numpy(float),rowvar=False,ddof=1))
        for name,kind,role,cov,text_weight in estimates:
            marginal_change=float(np.max(np.abs(np.diag(cov)-np.diag(base))))
            if not np.allclose(np.diag(cov),np.diag(base),rtol=1e-12,atol=1e-16):raise ValueError('Marginal variances changed')
            rows.append({'decision_date':window['decision_date'],'test_start':str(test.index[0].date()),'test_end':str(test.index[-1].date()),
                'run':name,'kind':kind,'arm_role':role,'text_weight':text_weight,'trailing_price_mean_correlation':rho,
                'max_absolute_marginal_variance_change':marginal_change,**window_losses(cov,realized,w)})
    if not rows:raise ValueError('No windows')
    frame=pd.DataFrame(rows);baseline=frame[frame.kind=='price_only'].set_index('decision_date')
    aggregate=[]
    for (name,kind),group in frame.groupby(['run','kind'],sort=False):
        if len(group)!=len(windows) or group.decision_date.duplicated().any():raise ValueError('Incomplete estimator windows')
        entry={'run':name,'kind':kind,'arm_role':group.arm_role.iloc[0],'text_weight':float(group.text_weight.iloc[0]),'windows':len(group)}
        for loss in LOSSES:
            value=float(group[loss].mean());ref=float(baseline[loss].mean())
            entry['mean_'+loss]=value
            entry[loss+'_improvement_vs_price_only']=1-value/ref if ref>0 else None
            entry[loss+'_windows_better_than_price_only']=int(sum(r[loss]<baseline.loc[r['decision_date'],loss] for r in group.to_dict('records')))
        aggregate.append(entry)
    comparisons=[]
    lookup={(r['run'],r['kind']):r for r in aggregate}
    for name in names:
        full=lookup[name,'calibrated_cosine']
        references=[('price_only',lookup['price_only','price_only']),('diagonal_target',lookup['diagonal_target','diagonal_target']),
            ('price_constant_correlation',lookup['price_constant_correlation','price_constant_correlation']),
            ('paired_calibrated_level_control',lookup[name,'calibrated_level_control']),('paired_raw_cosine',lookup[name,'raw_cosine'])]
        for label,reference in references:
            entry={'run':name,'arm_role':full['arm_role'],'reference':label,'windows':len(windows)}
            for loss in LOSSES:
                a=full['mean_'+loss];b=reference['mean_'+loss]
                entry[loss+'_improvement_vs_reference']=1-a/b if b>0 else None
            comparisons.append(entry)
    return {'window_losses':rows,'aggregate_losses':aggregate,'calibration_fits':fits,'comparisons':comparisons}
