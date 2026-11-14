"""Run the frozen descriptive risk snapshot after auditing local market inputs."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from secstab.risk_snapshot import compute_snapshot
from audit_market_pilot import audit,sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--market',default='data/market/yahoo_pilot_v2')
    p.add_argument('--corpus',default='data/corpus_extracted_v1.json')
    p.add_argument('--evidence',default='results/pilot_2026-11-03_complete/verified_evidence.json')
    p.add_argument('--config',default='configs/risk_snapshot_v1.json')
    p.add_argument('--output',default='runs/risk_snapshot_v1')
    args=p.parse_args();output=Path(args.output)
    if output.exists():raise FileExistsError('Preserve existing results; use another output directory')
    receipt,panel,evidence=audit(args.market,args.corpus,args.evidence)
    config=json.loads(Path(args.config).read_text())
    cutoff=pd.Timestamp(config['asof_date']+' 16:00',tz='America/New_York')
    if any(pd.Timestamp(d['accepted_at'])>cutoff for d in evidence['documents']):
        raise ValueError('Source filing accepted after price snapshot; no trading eligibility approval is inferred')
    result=compute_snapshot(panel,evidence['similarities'],config)
    result['receipt']={'market_audit':receipt,'config_sha256':sha(args.config),
        'code_sha256':{p:sha(Path(__file__).resolve().parents[1]/p) for p in ['scripts/run_risk_snapshot.py','scripts/audit_market_pilot.py','src/secstab/risk_snapshot.py','src/secstab/financial.py']},
        'packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scikit-learn','exchange-calendars']},
        'chronology':'Retrospective: saved embeddings were generated after the price snapshot. Unknown training cutoffs, pending permanent links and unapproved trading eligibility remain.',
        'kernel_interpretation':'Raw cosine is not an estimated return correlation; level and anisotropy differ by encoder. This is an uncalibrated mechanical mapping.',
        'data_policy':'Only aggregate derived results written; no provider observations copied'}
    output.mkdir(parents=True,exist_ok=False)
    for name in ['summary','matrices','receipt']:
        (output/(name+'.json')).write_text(json.dumps(result[name],indent=2,allow_nan=False)+'\n',encoding='utf-8')
    for name in ['settings','contrasts','stock_descriptives']:
        pd.DataFrame(result[name]).to_csv(output/(name+'.csv'),index=False,float_format='%.17g')
    print(json.dumps(result['summary'],indent=2));print('Saved:',output)


if __name__=='__main__':main()
