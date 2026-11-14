"""Summarize the already-run full-kernel versus score-level control contrast.

No new estimators, outcome windows, fits or model inference. Negative improvement
means the full kernel has higher error than the matching score-level control.
"""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd


def compare(root,output):
    root=Path(root);output=Path(output)
    if output.exists():raise FileExistsError('Preserve existing comparison output')
    summary=json.loads((root/'summary.json').read_text())
    table=pd.read_csv(root/'aggregate_losses.csv',float_precision='round_trip')
    window=pd.read_csv(root/'window_losses.csv',float_precision='round_trip')
    primary=table[(table.kernel_type=='raw_cosine')&(table.arm_role=='primary')&(table.text_weight==summary['primary_text_weight'])]
    rows=[]
    for _,full in primary.iterrows():
        controls=table[(table.run==full.run)&(table.kernel_type=='score_level_control')&(table.text_weight==full.text_weight)]
        if len(controls)!=1:raise ValueError('Need one matching level control')
        control=controls.iloc[0]
        if full.windows!=summary['windows'] or control.windows!=summary['windows']:raise ValueError('Window count mismatch')
        row={'run':full.run,'text_weight':float(full.text_weight),'windows':int(full.windows)}
        for metric in ['portfolio_variance_squared_error','covariance_entry_mse','covariance_off_diagonal_mse']:
            a=float(full['mean_'+metric]);b=float(control['mean_'+metric])
            row[metric+'_full_to_level_error_ratio']=a/b if b>0 else None
            row[metric+'_improvement_vs_level_control']=1-a/b if b>0 else None
            f=window[(window.run==full.run)&(window.kernel_type=='raw_cosine')&(window.text_weight==full.text_weight)].set_index('decision_date')[metric]
            c=window[(window.run==full.run)&(window.kernel_type=='score_level_control')&(window.text_weight==full.text_weight)].set_index('decision_date')[metric]
            if f.index.has_duplicates or c.index.has_duplicates or set(f.index)!=set(c.index) or len(f)!=summary['windows']:raise ValueError('Window identity mismatch')
            row[metric+'_windows_better_than_level_control']=int((f<c.reindex(f.index)).sum())
        rows.append(row)
    if len(rows)!=summary['primary_representations']:raise ValueError('Missing primary representation')
    output.mkdir(parents=True,exist_ok=False)
    pd.DataFrame(rows).to_csv(output/'comparison.csv',index=False,float_format='%.17g')
    receipt={'scope':'contrast of frozen results only; no new financial experiment',
        'metric':'1 - mean_full_kernel_loss / mean_score_level_control_loss; negative means higher full-kernel error',
        'source_sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ['aggregate_losses.csv','window_losses.csv','summary.json']},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'no_significance_test':True}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(pd.DataFrame(rows)[['run','portfolio_variance_squared_error_improvement_vs_level_control','covariance_entry_mse_improvement_vs_level_control']].to_string(index=False))
    print('Saved:',output)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',default='results/risk_accuracy_2026-11-14')
    p.add_argument('--output',default='runs/score_level_comparison_v1')
    a=p.parse_args();compare(a.results,a.output)


if __name__=='__main__':main()
