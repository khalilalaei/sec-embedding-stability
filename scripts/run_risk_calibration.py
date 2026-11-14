"""Run the fixed exploratory past-only shrinkage calibration and controls."""
import argparse
from datetime import datetime,timezone
import importlib.metadata
import json
from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from secstab.risk_accuracy import assumed_eligibility,evaluation_windows
from secstab.risk_calibration import evaluate_calibration
from audit_market_pilot import audit,sha

PROTOCOL_COMMIT='ab048039081292e123d297019721ba503448e5ed'
REFERENCE_CONFIG_SHA256='6172de362e58e142bc0aace24bf172d49e21e19ffd313b5305fcf6f4f620fbfa'


def main():
    import exchange_calendars as xcals
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--market',default='data/market/yahoo_pilot_v2');p.add_argument('--corpus',default='data/corpus_extracted_v1.json')
    p.add_argument('--evidence',default='results/pilot_2026-11-03_complete/verified_evidence.json')
    p.add_argument('--config',default='configs/risk_calibration_v1.json');p.add_argument('--output',default='runs/risk_calibration_v1')
    a=p.parse_args();output=Path(a.output)
    if output.exists():raise FileExistsError('Preserve existing results; use another output directory')
    started=datetime.now(timezone.utc).isoformat();audit_receipt,panel,evidence=audit(a.market,a.corpus,a.evidence)
    config=json.loads(Path(a.config).read_text());dates=pd.to_datetime(config['candidate_month_ends'])
    earliest=min(pd.Timestamp(d['accepted_at']).tz_convert('America/New_York').tz_localize(None).normalize() for d in evidence['documents'])
    calendar=xcals.get_calendar('XNYS',start=min(earliest,panel.index[0])-pd.Timedelta(days=10),end=max(dates.max(),panel.index[-1])+pd.Timedelta(days=40))
    sessions=pd.DatetimeIndex(calendar.sessions).tz_localize(None)
    closes=pd.Series([calendar.session_close(d) for d in sessions],index=sessions)
    eligibility=assumed_eligibility(evidence['documents'],closes);windows,excluded=evaluation_windows(panel,closes,eligibility,config)
    result=evaluate_calibration(panel,evidence['similarities'],config,windows)
    primary=[r for r in result['aggregate_losses'] if r['kind']=='calibrated_cosine' and r['arm_role']=='primary']
    def better(reference,metric):
        return sum(r[metric+'_improvement_vs_reference'] is not None and r[metric+'_improvement_vs_reference']>0 for r in result['comparisons'] if r['arm_role']=='primary' and r['reference']==reference)
    summary={'scope':config['scope'],'windows':len(windows),'evaluation_return_dates':sum(w['test_days'] for w in windows),
        'primary_text_weight':config['primary_text_weight'],'primary_representations':len(primary),
        'primary_with_lower_portfolio_error_vs_price_only':better('price_only','portfolio_variance_squared_error'),
        'primary_with_lower_portfolio_error_vs_diagonal_target':better('diagonal_target','portfolio_variance_squared_error'),
        'primary_with_lower_portfolio_error_vs_price_constant_correlation':better('price_constant_correlation','portfolio_variance_squared_error'),
        'primary_with_lower_portfolio_error_vs_paired_level_control':better('paired_calibrated_level_control','portfolio_variance_squared_error'),
        'primary_with_lower_covariance_error_vs_price_only':better('price_only','covariance_entry_mse'),
        'primary_with_lower_covariance_error_vs_diagonal_target':better('diagonal_target','covariance_entry_mse'),
        'primary_with_lower_covariance_error_vs_price_constant_correlation':better('price_constant_correlation','covariance_entry_mse'),
        'primary_with_lower_covariance_error_vs_paired_level_control':better('paired_calibrated_level_control','covariance_entry_mse'),
        'excluded_candidates':excluded,'inference':'exploratory method development on already-inspected windows; no fresh validation or financial superiority claim'}
    receipt={'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat(),'reference_protocol_commit':PROTOCOL_COMMIT,
        'config_sha256':sha(a.config),'reference_config_sha256':REFERENCE_CONFIG_SHA256,
        'matches_reference_protocol_config':sha(a.config)==REFERENCE_CONFIG_SHA256,'market_audit':audit_receipt,
        'code_sha256':{p:sha(Path(__file__).resolve().parents[1]/p) for p in ['src/secstab/risk_calibration.py','src/secstab/risk_accuracy.py','src/secstab/financial.py','scripts/run_risk_calibration.py','scripts/audit_market_pilot.py']},
        'packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scikit-learn','exchange-calendars']},
        'chronology':config['chronology_limit'],'data_policy':'aggregate derived results only; original review statuses unchanged'}
    output.mkdir(parents=True,exist_ok=False)
    for name,obj in [('summary',summary),('receipt',receipt),('windows',windows),('excluded_candidates',excluded),('assumed_eligibility',eligibility)]:
        (output/(name+'.json')).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    for name in ['window_losses','aggregate_losses','calibration_fits','comparisons']:
        pd.DataFrame(result[name]).to_csv(output/(name+'.csv'),index=False,float_format='%.17g')
    print(json.dumps(summary,indent=2));print('Saved:',output)


if __name__=='__main__':main()
