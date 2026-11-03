"""Exploratory peer-count supplement from frozen audited similarity matrices.

Keeps k=2 primary. Uniform-random overlap is a combinatorial reference only,
not a financial comparator, significance test or realistic model of disclosures.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from audit_pilot_results import recompute_comparison

CONTRASTS=['e5_vs_bge_192','e5_vs_qwen_192_gpu','bge_vs_qwen_192',
           'e5_192_vs_320','bge_192_vs_320','qwen_192_vs_320_gpu']


def overlap_reference(n,k,observed):
    if not 1<=k<n-1:raise ValueError('Need 1 <= k < n-1')
    if not np.isfinite(observed) or not 0<=observed<=1:raise ValueError('Invalid overlap')
    expected=k/(n-1)
    return expected,(observed-expected)/(1-expected)


def build(evidence,source_hash,ks):
    ids=[r['document_id'] for r in evidence['documents']]
    names={r['document_id']:r['ticker'] for r in evidence['documents']}
    contrasts={r['comparison_id']:r for r in evidence['comparisons']}
    summaries=[];details=[]
    for cid in CONTRASTS:
        original=contrasts[cid];a,b=original['run_a'],original['run_b']
        for k in ks:
            c=recompute_comparison(np.asarray(evidence['similarities'][a]),np.asarray(evidence['similarities'][b]),ids,k)
            memberships=sum(len(set(r['peers_a'])&set(r['peers_b'])) for r in c['companies'])
            reference,normalized=overlap_reference(len(ids),k,c['mean_top_k_overlap'])
            summaries.append({'comparison_id':cid,'k':k,'retained_memberships':memberships,
                'total_memberships':len(ids)*k,'mean_top_k_overlap':c['mean_top_k_overlap'],
                'mean_top_k_jaccard':c['mean_top_k_jaccard'],
                'uniform_independent_reference_overlap':reference,'normalized_excess_overlap':normalized,
                'spearman_pair_similarity':c['spearman_pair_similarity'],
                'mean_absolute_similarity_change':c['mean_absolute_similarity_change']})
            for row in c['companies']:
                details.append({'comparison_id':cid,'k':k,'ticker':names[row['document_id']],
                    'peers_a':[names[x] for x in row['peers_a']],
                    'peers_b':[names[x] for x in row['peers_b']],
                    'overlap':row['overlap'],'jaccard':row['jaccard'],
                    'margin_a':row['margin_a'],'margin_b':row['margin_b']})
    return {'scope':'Post hoc exploratory peer-count check; k=2 remains primary; no financial outcomes',
            'source_evidence_sha256':source_hash,'n_companies':len(ids),'ks':ks,
            'reference_assumption':'Two independent uniformly sampled k-element subsets of n-1 possible peers, per focal company.',
            'reference_formula':'E[intersection/k]=k/(n-1); normalized_excess=(observed-reference)/(1-reference)',
            'limitations':'Not a significance test. Scores, configurations and company pairs are dependent. Larger sets permit re-entry of peers and raise expected overlap mechanically. No inference rerun.',
            'summaries':summaries,'companies':details}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',default='results/pilot_2026-11-03_complete/verified_evidence.json')
    p.add_argument('--ks',nargs='+',type=int,default=[1,2,3,5])
    p.add_argument('--output',default='results/peer_count_2026-11-03')
    args=p.parse_args()
    root=Path(args.output)
    if root.exists():raise ValueError('Output exists; preserve earlier evidence')
    source=Path(args.evidence)
    result=build(json.loads(source.read_text()),hashlib.sha256(source.read_bytes()).hexdigest(),args.ks)
    root.mkdir(parents=True)
    (root/'verified_sensitivity.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with (root/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(result['summaries'][0]));w.writeheader();w.writerows(result['summaries'])
    for r in result['summaries']:
        if r['comparison_id']=='e5_vs_qwen_192_gpu':print(json.dumps(r))


if __name__=='__main__':main()
