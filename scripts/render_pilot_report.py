"""Build the descriptive report, CSV tables and SVG from audited pilot evidence."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np

ORDER=['tfidf_vs_e5_192','e5_192_vs_320','bge_192_vs_320','qwen_192_vs_320_gpu','e5_vs_bge_192','e5_vs_qwen_192_gpu','bge_vs_qwen_192','e5_cpu_vs_gpu_192']
LABELS={'tfidf_vs_e5_192':'TF-IDF vs E5 (192)', 'e5_192_vs_320':'E5: 192 vs 320',
'bge_192_vs_320':'BGE: 192 vs 320', 'qwen_192_vs_320_gpu':'Qwen: 192 vs 320',
'e5_vs_bge_192':'E5 vs BGE (192)', 'e5_vs_qwen_192_gpu':'E5 vs Qwen (192)',
'bge_vs_qwen_192':'BGE vs Qwen (192)', 'e5_cpu_vs_gpu_192':'E5: CPU vs GPU (192)'}


def figure(evidence):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.hashsalt':'secstab-pilot-20261103'})
    byid={c['comparison_id']:c for c in evidence['comparisons']}
    order=[cid for cid in ORDER if cid in byid]
    fig,axes=plt.subplots(1,2,figsize=(11.2,4.8 if len(order)==6 else 6.0),sharey=True,gridspec_kw={'width_ratios':[1,1]})
    y=np.arange(len(order))
    colors=['#a0aec0' if cid.startswith('tfidf') else '#9ca3af' if 'cpu_vs_gpu' in cid else '#187a86' if '192_vs_320' in cid else '#2166ac' for cid in order]
    for ax,key,title in zip(axes,['spearman_pair_similarity','mean_top_k_overlap'],['Similarity-rank agreement','Top-two peer membership retained']):
        values=[byid[k][key] for k in order]
        ax.barh(y,values,color=colors,height=.60)
        ax.set_xlim(0,1.14)
        ax.set_xticks([0,.25,.5,.75,1])
        ax.grid(axis='x',alpha=.15)
        ax.set_axisbelow(True)
        ax.set_title(title,pad=12,fontweight='bold',fontsize=11)
        for i,(v,cid) in enumerate(zip(values,order)):
            text=f'{v:.3f}' if key=='spearman_pair_similarity' else f"{byid[cid]['retained_memberships']}/24"
            ax.text(v+.018,i,text,va='center',fontsize=10)
        for side in ['top','right','left']:ax.spines[side].set_visible(False)
        ax.tick_params(axis='y',length=0)
    axes[0].set_yticks(y,[LABELS[k] for k in order]);axes[0].invert_yaxis()
    axes[0].set_xlabel('Spearman correlation');axes[1].set_xlabel('Mean peer-set overlap')
    fig.suptitle('SEC Risk Factors: stable global rankings, changing local peers',x=.035,ha='left',fontsize=14,fontweight='bold')
    fig.text(.035,.018,'12 deliberately selected companies; k = 2. Descriptive pilot, no uncertainty intervals or financial evaluation.',fontsize=9,color='#4b5563')
    fig.subplots_adjust(left=.235,right=.97,top=.82,bottom=.16,wspace=.15)
    return fig


def write_csv(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def render(evidence,repo):
    repo=Path(repo)
    complete=evidence['verification'].get('initial_chunk_grid_complete',False)
    series='pilot_2026-11-03_complete' if complete else 'pilot_2026-11-03'
    archive_name='pilot-results-complete.zip' if complete else 'pilot-results.zip'
    result_dir=repo/'results'/series;result_dir.mkdir(parents=True,exist_ok=True)
    report_dir=repo/'reports';(report_dir/'figures').mkdir(parents=True,exist_ok=True)
    byid={c['comparison_id']:c for c in evidence['comparisons']}
    order=[cid for cid in ORDER if cid in byid]
    summary=[];company_rows=[]
    for cid in order:
        c=byid[cid]
        summary.append({key:c[key] for key in ['comparison_id','run_a','run_b','spearman_pair_similarity','mean_top_k_overlap','mean_top_k_jaccard','mean_absolute_similarity_change','retained_memberships','changed_peer_sets','changed_closest_peers','changed_peer_orders']})
        for r in c['companies']:
            company_rows.append({'comparison_id':cid,'ticker':r['ticker'],'peers_a':' | '.join(r['peers_a_tickers']),'peers_b':' | '.join(r['peers_b_tickers']),
                                 **{k:r[k] for k in ['overlap','jaccard','margin_a','margin_b','set_changed','order_changed','closest_peer_changed']}})
    write_csv(result_dir/'comparison_summary.csv',summary,list(summary[0]))
    write_csv(result_dir/'company_peer_changes.csv',company_rows,list(company_rows[0]))
    fig=figure(evidence)
    fig.savefig(report_dir/'figures/pilot_stability_2026-11-03.svg',metadata={'Date':None})
    import matplotlib.pyplot as plt
    plt.close(fig)
    lines=['# SEC embedding stability: pilot results — 2026-11-03','',
    '**Finding:** global company-similarity rankings agree strongly across the three neural families, while top-two peer membership changes for specific companies. Economic or predictive value has not been tested.','',
    'These are descriptive results on 12 deliberately selected companies, one real 10-K Item 1A section per company. Original reporting periods range from November 2025 through June 2026. The 66 unordered company pairs are dependent observations, not 66 independent securities. Source extraction has AI-assisted boundary/source review, not an independent human audit.','',
    '![Pilot stability summary](figures/pilot_stability_2026-11-03.svg)','',
    '## Recomputed comparisons','',
    '| Comparison | Rank correlation | Retained memberships | Changed peer sets / 12 | Changed closest peers / 12 | Jaccard |',
    '|---|---:|---:|---:|---:|---:|']
    for cid in order:
        c=byid[cid]
        lines.append(f"| {LABELS[cid]} | {c['spearman_pair_similarity']:.6f} | {c['retained_memberships']}/24 | {c['changed_peer_sets']} | {c['changed_closest_peers']} | {c['mean_top_k_jaccard']:.6f} |")
    lines += ['',
    'Peer memberships are directed company-to-peer selections: 12 firms × 2 slots = 24. A changed set can replace either one or both members; a rank-order change can occur with no set change. Overlap is not a measure of economic correctness. Cross-model absolute cosine movements are exported as descriptive numbers only: the score scales differ.','',
    'E5 uses mean pooling, BGE CLS pooling, and Qwen last-token pooling, as recorded by the pinned SentenceTransformer checkpoints. All neural inference is recorded as float32; normalized document vectors are stored as float64 by the aggregation helper. Prefixes and model-specific pooling are part of the model-family configuration, so these comparisons do not isolate architecture alone.','',
    '## Key observations','',
    '- E5 192 versus 320: three companies change peer sets (JNJ, CAT, TGT); CAT also changes its closest peer. Similarity-rank correlation is 0.991567 despite these discrete changes.',
    *(['- BGE 192 versus 320: JNJ replaces Walmart with Deere; DE replaces Walmart with Caterpillar and changes its closest peer from Target to Caterpillar.',
       '- Qwen 192 versus 320: only Target changes its set, replacing Deere with Caterpillar; its closest peer remains Walmart.',
       '- Across the three chunk contrasts, Qwen retains the most memberships while BGE has the highest rank correlation. These measure different aspects of stability; the pilot does not identify a generally superior model.'] if complete else []),
    '- E5 versus BGE: two companies change peer sets (CAT and DE). CAT replaces one member; DE replaces both. That yields three lost memberships, not three changed companies.',
    '- E5 versus Qwen: five companies replace one member each (XOM, JNJ, MRK, CAT, DE). DE also changes its closest peer.',
    '- BGE versus Qwen: four sets change (XOM, JNJ, MRK, DE), while CAT only reverses its two peers. DE replaces both members. This has the same 19/24 retention as E5 versus Qwen but a different distribution of changes.',
    '- TF-IDF versus E5: six sets change; DE retains its set but reverses the order. TF-IDF identifies each deliberately selected industry partner as the closest peer (12/12); this selection diagnostic is not ground-truth financial performance.',
    '- The E5 CPU/environment versus GPU/environment check preserves all peer sets and pair-similarity ranks. Mean absolute cosine difference is 5.093662662365843e-08. CPU and GPU PyTorch versions differ, so this checks the combined environment/device change for this E5 arm, not an isolated hardware effect or a universal guarantee.',
    '- Small second-versus-third margins signal vulnerability, not a guaranteed switch: Chevron has a smaller initial margin than some changed companies but retains its set in the E5 budget contrast.','',
    '## Every changed peer order','',
    'Peer lists below are ordered closest first. The full company CSV also contains unchanged rows and both boundary margins.','']
    for cid in order:
        c=byid[cid];changed=[r for r in c['companies'] if r['order_changed']]
        lines += ['### '+LABELS[cid],'']
        if not changed:
            lines += ['No peer membership or order changes.',''];continue
        lines += ['| Company | Run A peers | Run B peers | Set changed? | Closest changed? | Margin A | Margin B |','|---|---|---|---|---|---:|---:|']
        for r in changed:
            lines.append(f"| {r['ticker']} | {', '.join(r['peers_a_tickers'])} | {', '.join(r['peers_b_tickers'])} | {'Yes' if r['set_changed'] else 'No'} | {'Yes' if r['closest_peer_changed'] else 'No'} | {r['margin_a']:.9f} | {r['margin_b']:.9f} |")
        lines += ['']
    lines += ['## What was verified','',
    f"- {evidence['verification']['verified_output_hashes']} saved run-output hashes and all {len(evidence['comparisons'])} comparison-to-manifest links match the uploaded evidence.",
    f"- {evidence['verification']['verified_source_artifacts']} distinct original/text/extraction-evidence files match the corpus's declared hashes using the earlier supplied source package.",
    f"- Corpus identities, order and snapshot contents match across all {len(evidence['runs'])} completed runs. Recorded code commits: {', '.join('`'+x+'`' for x in sorted({r['git_commit'] for r in evidence['runs'].values()}))}. No tracked working-tree modifications are recorded. The inference CLI and numerical core are unchanged across these commits. Earlier GPU runs recorded an untracked `.venv-gpu/` directory, which is now ignored.",
    '- Saved neural embeddings are finite, row-normalized, and reproduce each saved cosine matrix to numerical precision. Each saved peer list and margin was recomputed.',
    '- All 192-budget neural run records have identical 890 source chunks; all available 320-budget arms have identical 510 source chunks. Every source-span hash and complete nonoverlapping character coverage were checked.',
    '- TF-IDF term counts, vocabulary, document frequencies, IDF values, normalization and the similarity matrix were rebuilt from the exact extracted source text.',
    f"- All {len(evidence['comparisons'])} comparison summaries and {12*len(evidence['comparisons'])} company-level comparison rows were recomputed from matrices using a separate ranking implementation.",'',
    '**Verification boundary:** this is the same assistant reviewing supplied artifacts. Neural inference, pretrained weight hashes and tokenizer-budget counting were not independently rerun. A recorded revision identifies the requested checkpoint; cached model weights themselves were not supplied. The two source parsers used earlier share selection/cleanup rules, so their agreement is not an independent validation of those rules.','',
    '## Recorded run configurations','',
    '| Run | Model / representation | Budget | Device | PyTorch | Batch | Source chunks |',
    '|---|---|---:|---|---|---:|---:|']
    for name,m in evidence['runs'].items():
        settings=m.get('settings',{})
        lines.append(f"| {name} | {settings.get('model',{}).get('key','TF-IDF')} | {settings.get('total_token_budget','—')} | {settings.get('device','CPU')} | {settings.get('torch_version','not used')} | {m.get('batch_size','—')} | {m.get('chunk_count','—')} |")
    lines += ['',
    'The GPU identifies as NVIDIA GeForce RTX 3050 Laptop GPU, with recorded CUDA runtime 12.6. The user-reported 4 GB GPU memory is separate from system RAM. BGE–Qwen spans CPU/GPU environments; the E5 check is reassuring but is not a BGE-specific GPU control. No speed, memory-usage or cost benchmark is claimed.','',
    'Budgets are total tokenizer lengths, including prefixes and special tokens, not words or body-token counts. Source spans are shared across the locked tokenizers. Qwen uses a fixed symmetric instruction; no instruction sensitivity test has run. Aggregation is an equal mean of normalized chunk vectors followed by document L2 normalization. Each arm has one fixed-weight inference, not independent training-seed replications.','',
    '## Evidence and reproduction','',
    '- [Audited matrices, run receipts, hashes and all comparison rows](../results/pilot_2026-11-03/verified_evidence.json)',
    '- [Comparison CSV](../results/pilot_2026-11-03/comparison_summary.csv)',
    '- [All company peer changes and margins](../results/pilot_2026-11-03/company_peer_changes.csv)',
    '- [Exact recorded model register](../configs/models.pilot_2026-11-03.lock.json)',
    '- [Offline audit script](../scripts/audit_pilot_results.py)',
    '- [Report/figure renderer](../scripts/render_pilot_report.py)','',
    'The curated evidence contains matrices and sanitized receipts, not local absolute paths, raw filings, full source text, model weights or full environment directories. Original upload hashes are receipts for the preserved user archives; they are not hashes of normalized report files. Full hash/source verification requires the original `pilot-results-complete.zip` and matching source/extraction files. The publicized table/figure can be regenerated from the curated JSON without model inference.','',
    '```powershell',
    '.\\.venv\\Scripts\\python.exe -m pip install -e ".[report]"',
    '.\\.venv\\Scripts\\python.exe scripts/audit_pilot_results.py --archive pilot-results-complete.zip --source-project . --output audit_check.json',
    '.\\.venv\\Scripts\\python.exe scripts/render_pilot_report.py --evidence results/pilot_2026-11-03/verified_evidence.json --repo .',
    '```','',
    '## Limits and next experiments','',
    'This pilot does not establish incremental financial value, causality, model superiority, historical tradability or absence of look-ahead bias. It has one selected filing per company, mixed reporting periods, no historical point-in-time index sample, unknown model training/fine-tuning cutoffs, no financial targets and no held-out economic evaluation. TF-IDF was fitted to the whole descriptive corpus; that fit rule is unsuitable for a claimed historical forecast. No significance test or uncertainty interval is inferred from dependent company pairs.','',
    ('The initial three-model, two-budget grid is complete: E5 and BGE contrasts use their original CPU environment, and Qwen uses its GPU environment at both budgets. Third-party package versions, Python, inference settings, precision and batch size match within each model’s chunk contrast. BGE’s project-distribution metadata changes from 0.1.0 to 0.2.0; the inference CLI and numerical core are byte-identical across its recorded commits. This metadata exception is logged explicitly. Additional instruction, boundary/overlap and aggregation perturbations remain unrun. Next freeze the financial task, chronology, controls, data sources and inference plan with the team before expanding to point-in-time covariance/risk, volatility or return tests.' if complete else 'Finish the BGE and Qwen chunk contrasts before freezing the next financial protocol.'),'']
    lines=[line.replace('pilot-results-complete.zip',archive_name) for line in lines]
    if complete:
        lines[2:2]=['**Snapshot:** completed initial model/chunk grid; eight runs, eight comparisons. [Initial six-comparison report](https://github.com/khalilalaei/sec-embedding-stability/blob/b7d6998ccea715791e7b218a0fb43b14cd351e81/reports/pilot_stability_2026-11-03.md) and its original evidence remain preserved.','']
        lines=[line.replace('../results/pilot_2026-11-03/',f'../results/{series}/').replace('--evidence results/pilot_2026-11-03/','--evidence results/'+series+'/') for line in lines]
    (report_dir/'pilot_stability_2026-11-03.md').write_text('\n'.join(lines),encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',default='results/pilot_2026-11-03_complete/verified_evidence.json')
    p.add_argument('--repo',default='.')
    args=p.parse_args()
    render(json.loads(Path(args.evidence).read_text(encoding='utf-8')),args.repo)


if __name__=='__main__':main()
