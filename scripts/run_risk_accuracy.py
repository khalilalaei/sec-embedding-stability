"""Run the frozen assumption-based subsequent-window risk accuracy diagnostic."""
import argparse
from datetime import datetime,timezone
import importlib.metadata
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from secstab.risk_accuracy import assumed_eligibility,evaluation_windows,evaluate_accuracy
from audit_market_pilot import audit,sha

PROTOCOL_COMMIT='0d6d166d13d14dcda89771a61bf59b5b7627bbc8'
REFERENCE_CONFIG_SHA256='6723bd7b64ff8319e552211d9735d02d1ac155f34c325a84c6c2ec916cdd4654'


def main():
    import exchange_calendars as xcals
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--market',default='data/market/yahoo_pilot_v2');p.add_argument('--corpus',default='data/corpus_extracted_v1.json')
    p.add_argument('--evidence',default='results/pilot_2026-11-03_complete/verified_evidence.json')
    p.add_argument('--config',default='configs/risk_accuracy_v1.json');p.add_argument('--output',default='runs/risk_accuracy_v1')
    a=p.parse_args();output=Path(a.output)
    if output.exists():raise FileExistsError('Preserve existing results; use another output directory')
    started=datetime.now(timezone.utc).isoformat()
    audit_receipt,panel,evidence=audit(a.market,a.corpus,a.evidence)
    config=json.loads(Path(a.config).read_text())
    dates=pd.to_datetime(config['candidate_month_ends'])
    earliest=min(pd.Timestamp(d['accepted_at']).tz_convert('America/New_York').tz_localize(None).normalize() for d in evidence['documents'])
    calendar=xcals.get_calendar('XNYS',start=min(earliest,panel.index[0])-pd.Timedelta(days=10),end=max(dates.max(),panel.index[-1])+pd.Timedelta(days=40))
    sessions=pd.DatetimeIndex(calendar.sessions).tz_localize(None)
    closes=pd.Series([calendar.session_close(d) for d in sessions],index=sessions)
    eligibility=assumed_eligibility(evidence['documents'],closes)
    windows,excluded=evaluation_windows(panel,closes,eligibility,config)
    results=evaluate_accuracy(panel,evidence['similarities'],config,windows)
    primary=[r for r in results['aggregate_losses'] if r['kernel_type']=='raw_cosine' and r['arm_role']=='primary' and r['text_weight']==config['primary_text_weight']]
    baseline=next(r for r in results['aggregate_losses'] if r['run']=='price_only')
    summary={'scope':config['scope'],'windows':len(windows),'evaluation_return_dates':sum(w['test_days'] for w in windows),
        'excluded_candidates':excluded,'primary_text_weight':config['primary_text_weight'],
        'price_only_mean_portfolio_variance_squared_error':baseline['mean_portfolio_variance_squared_error'],
        'price_only_mean_covariance_entry_mse':baseline['mean_covariance_entry_mse'],
        'primary_representations':len(primary),
        'primary_representations_with_lower_portfolio_error':sum(r['portfolio_variance_squared_error_improvement_vs_price_only'] is not None and r['portfolio_variance_squared_error_improvement_vs_price_only']>0 for r in primary),
        'primary_representations_with_lower_covariance_error':sum(r['covariance_entry_mse_improvement_vs_price_only'] is not None and r['covariance_entry_mse_improvement_vs_price_only']>0 for r in primary),
        'inference':'descriptive only; no significance, model selection or independent holdout claim'}
    receipt={'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat(),'reference_protocol_commit':PROTOCOL_COMMIT,
        'reference_config_sha256':REFERENCE_CONFIG_SHA256,'matches_reference_protocol_config':sha(a.config)==REFERENCE_CONFIG_SHA256,
        'config_sha256':sha(a.config),'market_audit':audit_receipt,
        'code_sha256':{p:sha(Path(__file__).resolve().parents[1]/p) for p in ['src/secstab/risk_accuracy.py','src/secstab/financial.py','scripts/run_risk_accuracy.py','scripts/audit_market_pilot.py']},
        'packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scikit-learn','exchange-calendars']},
        'chronology':config['chronology_limit'],'eligibility_status':'explicit AI-assisted assumption only; original pending records unchanged',
        'data_policy':'aggregate derived results only; no provider observations copied'}
    output.mkdir(parents=True,exist_ok=False)
    for name,obj in [('summary',summary),('receipt',receipt),('windows',windows),('excluded_candidates',excluded),('assumed_eligibility',eligibility),('window_matrices',results['window_matrices'])]:
        (output/(name+'.json')).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    for name in ['window_losses','aggregate_losses']:
        pd.DataFrame(results[name]).to_csv(output/(name+'.csv'),index=False,float_format='%.17g')
    print(json.dumps(summary,indent=2));print('Saved:',output)


if __name__=='__main__':main()
