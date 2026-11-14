"""Audit a frozen local Yahoo collection; no requests or identity approvals.

Outputs aggregate diagnostics only. Provider observations remain local.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import importlib.metadata
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from secstab.financial import align_returns, validate_returns
from secstab.yahoo_pilot import adjusted_returns, provider_identity


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(root,corpus_path,evidence_path):
    import exchange_calendars as xcals
    root=Path(root)
    manifest=json.loads((root/'manifest.json').read_text())
    corpus=json.loads(Path(corpus_path).read_text(encoding='utf-8-sig'))
    evidence=json.loads(Path(evidence_path).read_text())
    if manifest['status']!='complete_data_collection_pending_review':raise ValueError('Incomplete collection')
    if sha(corpus_path)!=manifest['corpus_sha256'] or sha(corpus_path)!=evidence['corpus_sha256']:
        raise ValueError('Market and embedding corpus hashes differ')
    for group in ['source_files','outputs']:
        for name,digest in manifest[group].items():
            path=(root/name).resolve()
            if not path.is_relative_to(root.resolve()) or sha(path)!=digest:raise ValueError('Artifact hash mismatch: '+name)
    snapshot=json.loads((root/'corpus_snapshot.json').read_text())
    if snapshot!=corpus:raise ValueError('Corpus snapshot differs')
    if [r['document_id'] for r in corpus]!=[r['document_id'] for r in evidence['documents']]:
        raise ValueError('Matrix document order differs')
    symbols=[r['ticker'] for r in corpus]
    if len(set(symbols))!=12 or symbols!=manifest['completed_symbols']:raise ValueError('Unexpected universe')
    sessions=xcals.get_calendar('XNYS',start=pd.Timestamp(manifest['start_inclusive'])-pd.Timedelta(days=10),end=pd.Timestamp(manifest['end_exclusive'])+pd.Timedelta(days=10)).sessions_in_range(
        manifest['start_inclusive'],pd.Timestamp(manifest['end_exclusive'])-pd.Timedelta(days=1))
    calendar=pd.DatetimeIndex(sessions).tz_localize(None)
    saved=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(root/'trading_calendar.csv')['date']))
    if not saved.equals(calendar[1:]):raise ValueError('Saved return calendar mismatch')
    returns=validate_returns(pd.read_csv(root/'returns.csv',float_precision='round_trip'))
    panel=align_returns(returns,['YF:'+s for s in symbols],calendar[1:])
    if len(returns)!=panel.size:raise ValueError('Extra return observations')
    reviews=[];maximum_error=0.0
    for r in corpus:
        s=r['ticker'];table=pd.read_csv(root/f'provider_tables/{s}_history.csv',float_precision='round_trip')
        # Explicit UTC parse handles changing DST offsets; convert before date validation.
        table.index=pd.DatetimeIndex(pd.to_datetime(table.pop('Date'),utc=True)).tz_convert('America/New_York')
        metadata=json.loads((root/f'provider_tables/{s}_metadata.json').read_text())
        identity=provider_identity(metadata,s)
        rebuilt=adjusted_returns(table,s,calendar)
        error=float(np.max(np.abs(rebuilt['total_return'].to_numpy()-panel['YF:'+s].to_numpy())))
        maximum_error=max(maximum_error,error)
        if error>1e-12:raise ValueError('Saved returns differ from provider prices: '+s)
        for name in ['Close','Open','High','Low']:
            values=table[name].to_numpy(float)
            if not np.isfinite(values).all() or (values<=0).any():raise ValueError('Invalid OHLC: '+s)
        if (table['Low']>table[['Open','Close','High']].min(axis=1)+1e-5).any() or (table['High']<table[['Open','Close','Low']].max(axis=1)-1e-5).any():
            raise ValueError('Inconsistent OHLC: '+s)
        if not np.isfinite(table[['Volume','Dividends','Stock Splits']]).all().all() or (table[['Volume','Dividends','Stock Splits']]<0).any().any():raise ValueError('Invalid action/volume fields: '+s)
        series=panel['YF:'+s]
        reviews.append({'ticker':s,'sec_name':r['sec_name'],'provider_name':identity['provider_name'],
            'sec_ticker_membership':s in r['sec_tickers'],'price_rows':len(table),'return_rows':len(series),
            'dividend_event_count':int((table['Dividends']!=0).sum()),
            'splits':[{'date':str(d.date()),'ratio':float(v)} for d,v in table['Stock Splits'].items() if v!=0],
            'minimum_daily_proxy_return':float(series.min()),'maximum_daily_proxy_return':float(series.max())})
    return {'status':'numerical_and_lineage_checks_passed_not_identity_or_forecast_approval',
        'manifest_sha256':sha(root/'manifest.json'),'corpus_sha256':sha(corpus_path),
        'evidence_sha256':sha(evidence_path),'checked_artifact_count':sum(len(manifest[g]) for g in ['source_files','outputs']),
        'security_count':12,'return_dates':len(panel),'observations':panel.size,
        'first_return_date':str(panel.index[0].date()),'last_return_date':str(panel.index[-1].date()),
        'maximum_reconstruction_error':maximum_error,'missing_panel_cells':int(panel.isna().sum().sum()),
        'calendar_audit_version':importlib.metadata.version('exchange-calendars'),
        'identities':reviews,'scope':'AI-assisted numerical audit; no independent human/security-master review; no historical implementability approval'},panel,evidence


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--market',required=True);p.add_argument('--corpus',required=True)
    p.add_argument('--evidence',default='results/pilot_2026-11-03_complete/verified_evidence.json')
    p.add_argument('--output',required=True)
    args=p.parse_args()
    result,_,_=audit(args.market,args.corpus,args.evidence)
    with Path(args.output).open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='identities'},indent=2))


if __name__=='__main__':main()
