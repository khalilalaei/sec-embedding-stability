"""Yahoo adjusted-price proxy for the selected pilot, not a CRSP replacement.

No network call occurs on import. Preserve provider-parsed tables/metadata,
explicit adjustment settings and hashes; never overwrite a collection directory.
"""
import argparse
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from .financial import validate_returns,align_returns

HISTORY_OPTIONS={'interval':'1d','auto_adjust':False,'back_adjust':False,
                 'actions':True,'repair':False,'keepna':True,'rounding':False,
                 'timeout':30}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def metadata_snapshot(metadata):
    """Convert mappings without stringifying them or fetching lazy intraday keys."""
    if isinstance(metadata,str):
        try:metadata=json.loads(metadata)
        except json.JSONDecodeError as error:
            raise ValueError('Metadata was non-JSON text rather than a dictionary-like object') from error
    if not isinstance(metadata,Mapping):raise ValueError('Expected dictionary-like provider metadata')

    def convert(value):
        if isinstance(value,Mapping):
            # Iterating items() on HistoryMetadata eagerly loads tradingPeriods.
            return {str(key):convert(value[key]) for key in value if key!='tradingPeriods'}
        if isinstance(value,(list,tuple)):return [convert(x) for x in value]
        if isinstance(value,np.ndarray):return convert(value.tolist())
        if isinstance(value,np.generic):return convert(value.item())
        if value is None or value is pd.NaT:return None
        if isinstance(value,(str,bool,int)):return value
        if isinstance(value,float):return value if np.isfinite(value) else None
        if hasattr(value,'isoformat'):return value.isoformat()
        raise ValueError('Unsupported provider metadata value type: '+type(value).__name__)
    return convert(metadata)


def request_history(client,yf_module,start,end):
    """Use current exception config when present, with an older-version fallback."""
    debug=getattr(getattr(yf_module,'config',None),'debug',None)
    options=dict(HISTORY_OPTIONS)
    if debug is not None and hasattr(debug,'hide_exceptions'):
        previous=debug.hide_exceptions
        debug.hide_exceptions=False
        try:return client.history(start=start,end=end,**options)
        finally:debug.hide_exceptions=previous
    return client.history(start=start,end=end,raise_errors=True,**options)


def provider_identity(metadata,ticker):
    if not isinstance(metadata,Mapping):raise ValueError('Expected dictionary-like provider metadata: '+ticker)
    if str(metadata.get('symbol','')).upper()!=ticker.upper():raise ValueError('Provider symbol mismatch: '+ticker)
    if metadata.get('currency')!='USD':raise ValueError('Expected explicit USD metadata: '+ticker)
    if metadata.get('instrumentType')!='EQUITY':raise ValueError('Expected equity metadata: '+ticker)
    if metadata.get('exchangeTimezoneName')!='America/New_York':raise ValueError('Unexpected exchange timezone: '+ticker)
    return {'provider_symbol':metadata['symbol'],'provider_name':metadata.get('longName') or metadata.get('shortName'),
            'currency':metadata['currency'],'instrument_type':metadata['instrumentType'],
            'exchange':metadata.get('exchangeName'),'timezone':metadata['exchangeTimezoneName'],
            'link_status':'vendor_ticker_alias_only; issuer/share-class review pending; not PERMNO'}


def adjusted_returns(history,ticker,expected_dates):
    if history.empty or 'Adj Close' not in history or 'Close' not in history:
        raise ValueError('Missing explicit Close/Adj Close provider columns: '+ticker)
    if not isinstance(history.index,pd.DatetimeIndex):raise ValueError('Expected provider DatetimeIndex')
    dates=history.index
    if dates.tz is not None:
        dates=dates.tz_convert('America/New_York').tz_localize(None)
    if not dates.equals(dates.normalize()):raise ValueError('Non-midnight daily price labels')
    if dates.has_duplicates or not dates.is_monotonic_increasing:raise ValueError('Duplicate/unsorted provider price dates')
    expected=pd.DatetimeIndex(expected_dates)
    if not dates.equals(expected):
        missing=expected.difference(dates).strftime('%Y-%m-%d').tolist()
        extra=dates.difference(expected).strftime('%Y-%m-%d').tolist()
        raise ValueError(f'Price/calendar mismatch for {ticker}; missing={missing[:10]}, extra={extra[:10]}')
    prices=pd.to_numeric(history['Adj Close'],errors='raise').to_numpy(dtype=float)
    if len(prices)<2 or not np.isfinite(prices).all() or np.any(prices<=0):
        raise ValueError('Missing/nonpositive adjusted price: '+ticker)
    # Adj Close already contains provider adjustments: do not add dividends again.
    values=prices[1:]/prices[:-1]-1
    frame=pd.DataFrame({'date':dates[1:],'security_id':'YF:'+ticker,'total_return':values})
    return validate_returns(frame)


def assemble_tables(records,tables,metadata,calendar):
    ids=[];returns=[];links=[];summary=[]
    for r in records:
        ticker=r['ticker'];identity=provider_identity(metadata[ticker],ticker)
        frame=adjusted_returns(tables[ticker],ticker,calendar)
        ids.append('YF:'+ticker);returns.append(frame)
        links.append({'document_id':r['document_id'],'cik':r['cik'],'ticker':ticker,'security_id':'YF:'+ticker,
                      'link_start':str(calendar[0].date()),'link_end':str(calendar[-1].date()),
                      'review_status':'pending_vendor_identity_review','notes':identity['link_status']})
        summary.append({'ticker':ticker,**identity,'price_rows':len(tables[ticker]),'return_rows':len(frame),
                        'first_return_date':str(frame['date'].min().date()),'last_return_date':str(frame['date'].max().date())})
    combined=validate_returns(pd.concat(returns,ignore_index=True))
    panel=align_returns(combined,ids,calendar[1:])
    return combined,pd.DataFrame(links),summary,panel


def collect(args):
    import yfinance as yf
    import exchange_calendars as xcals
    output=Path(args.output)
    start,end=pd.Timestamp(args.start),pd.Timestamp(args.end)
    if start>=end or start!=start.normalize() or end!=end.normalize() or start.tz is not None or end.tz is not None:
        raise ValueError('Use increasing YYYY-MM-DD date labels; end is exclusive')
    records=json.loads(Path(args.corpus).read_text(encoding='utf-8-sig'))
    if len(records)!=12 or len({r['document_id'] for r in records})!=12 or len({r['ticker'] for r in records})!=12:
        raise ValueError('This collector is scoped to the reviewed 12-company pilot')
    for r in records:
        if r.get('review_status') not in {'passed','ai_assisted_passed'}:raise ValueError('Unreviewed source corpus')
        if not r['ticker'].isalnum():raise ValueError('Unexpected ticker/path syntax')
    sessions=xcals.get_calendar('XNYS').sessions_in_range(start,end-pd.Timedelta(days=1))
    calendar=pd.DatetimeIndex(sessions)
    if calendar.tz is not None:calendar=calendar.tz_localize(None)
    if len(calendar)<274:raise ValueError('Need at least 274 price sessions for a 252+21 return-window prototype')
    output.mkdir(parents=True,exist_ok=False)
    (output/'provider_tables').mkdir()
    manifest={'status':'started','scope':'exploratory selected-company Yahoo adjusted-price return proxy; not CRSP',
        'started_at':datetime.now(timezone.utc).isoformat(),'start_inclusive':args.start,'end_exclusive':args.end,
        'corpus_sha256':sha(args.corpus),'request_options':HISTORY_OPTIONS,
        'error_policy':'config.debug.hide_exceptions=False when available (restored after request), otherwise legacy raise_errors=True',
        'metadata_policy':'Convert Mapping to JSON objects; omit lazy tradingPeriods (intraday metadata not used for daily collection)',
        'packages':{p:importlib.metadata.version(p) for p in ['yfinance','exchange-calendars','pandas','numpy']},
        'calendar':'XNYS via exchange_calendars; explicit complete-session check',
        'return_formula':'AdjClose[t]/AdjClose[t-1]-1; no additional dividend/split adjustment',
        'source_artifact_scope':'yfinance-parsed history tables and metadata, NOT raw HTTP responses',
        'security_identity_scope':'YF:TICKER vendor-scoped aliases, not permanent security identifiers',
        'limitations':['No CRSP-style permanent historical security links or delisting-return coverage',
                      'Current-company selection and revised adjusted-price histories are not point-in-time historical data',
                      'Unknown model training cutoffs; historical tests remain retrospective',
                      'Provider terms apply; data stays local and is not committed to GitHub'],
        'source_files':{},'completed_symbols':[]}
    write(output/'manifest.json',manifest)
    tables={};metadata={}
    try:
        for r in records:
            ticker=r['ticker'];print('Downloading',ticker,flush=True)
            client=yf.Ticker(ticker)
            table=request_history(client,yf,args.start,args.end)
            path=output/'provider_tables'/f'{ticker}_history.csv'
            table.to_csv(path,index=True,float_format='%.17g')
            manifest['source_files'][path.relative_to(output).as_posix()]=sha(path)
            meta=client.get_history_metadata(repair=False)
            # Do not use default=str: newer HistoryMetadata is a Mapping, not dict.
            meta=metadata_snapshot(meta)
            path=output/'provider_tables'/f'{ticker}_metadata.json';write(path,meta)
            manifest['source_files'][path.relative_to(output).as_posix()]=sha(path)
            provider_identity(meta,ticker)
            adjusted_returns(table,ticker,calendar)
            tables[ticker]=table;metadata[ticker]=meta
            manifest['completed_symbols'].append(ticker);write(output/'manifest.json',manifest)
            time.sleep(1)
        returns,links,summary,panel=assemble_tables(records,tables,metadata,calendar)
        returns.assign(date=returns['date'].dt.strftime('%Y-%m-%d')).to_csv(output/'returns.csv',index=False,float_format='%.17g')
        pd.DataFrame({'date':calendar[1:].strftime('%Y-%m-%d')}).to_csv(output/'trading_calendar.csv',index=False)
        links.to_csv(output/'security_links.csv',index=False)
        write(output/'identity_review.json',summary)
        write(output/'corpus_snapshot.json',records)
        manifest.update(status='complete_data_collection_pending_review',completed_at=datetime.now(timezone.utc).isoformat(),
                        return_dates=len(panel),security_count=len(panel.columns),
                        outputs={p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name!='manifest.json'},
                        next_gate='Review issuer identities, adjustment/events and filing availability before financial evaluation')
        write(output/'manifest.json',manifest)
        print('Downloaded and calendar-validated 12-company adjusted-price proxy.',flush=True)
        print('Saved:',output,'; dates:',len(panel),'; security identities still require review.',flush=True)
    except Exception as error:
        manifest.update(status='failed_partial_collection_preserved',error_type=type(error).__name__,error=str(error))
        write(output/'manifest.json',manifest)
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',default='data/corpus_extracted_v1.json')
    p.add_argument('--start',default='2024-01-01')
    p.add_argument('--end',default='2026-11-03',help='Exclusive; default freezes observations through 2026-11-02')
    p.add_argument('--output',default='data/market/yahoo_pilot_v1')
    collect(p.parse_args())


if __name__=='__main__':main()
