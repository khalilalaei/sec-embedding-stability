"""Render aggregate risk-snapshot evidence; requires the optional report extra."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

LABELS={'pilot_tfidf':'TF-IDF','pilot_e5_192':'E5 192','pilot_e5_320':'E5 320',
    'pilot_bge_192':'BGE 192','pilot_bge_320':'BGE 320','pilot_qwen_192_gpu':'Qwen 192',
    'pilot_qwen_320_gpu':'Qwen 320','pilot_e5_192_gpu':'E5 GPU 192 (diagnostic)'}


def render(root,report,figure):
    root=Path(root);summary=json.loads((root/'summary.json').read_text())
    table=pd.read_csv(root/'settings.csv');contrasts=pd.read_csv(root/'contrasts.csv')
    primary=table[(table.text_weight==summary['primary_text_weight'])&(table.arm_role=='primary')]
    if len(primary)!=7 or len(table)!=40 or len(contrasts)!=8:raise ValueError('Unexpected frozen pilot shape')
    neural=primary[primary.run!='pilot_tfidf']
    low,high=100*neural.annualized_portfolio_sd.min(),100*neural.annualized_portfolio_sd.max()
    plt.rcParams['svg.hashsalt']='risk-snapshot-v1'
    fig,ax=plt.subplots(figsize=(8.6,4.7))
    colors=['#788493','#276a9d','#276a9d','#257b62','#257b62','#985281','#985281']
    bars=ax.bar([LABELS[x] for x in primary.run],100*primary.annualized_portfolio_sd,color=colors,width=.7)
    for bar,value in zip(bars,100*primary.annualized_portfolio_sd):ax.text(bar.get_x()+bar.get_width()/2,value+.22,f'{value:.2f}%',ha='center',fontsize=9)
    base=100*summary['baseline_annualized_portfolio_sd']
    ax.axhline(base,color='#202a34',linestyle='--',linewidth=1.3,label=f'Price-only baseline: {base:.2f}%')
    ax.set_ylim(0,21);ax.set_ylabel('Estimated annualized portfolio standard deviation (%)')
    ax.set_title('Same prices and equal weights; different text representations',loc='left',fontsize=13,pad=15)
    ax.spines[['top','right']].set_visible(False);ax.legend(loc='upper left',frameon=False,fontsize=9)
    ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.text(.13,.025,'Snapshot: 2026-11-02 | 252 trailing returns | text weight = 0.25 | retrospective, no accuracy test',fontsize=8)
    fig.tight_layout(rect=[0,.05,1,1]);Path(figure).parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(figure,metadata={'Date':None} if Path(figure).suffix=='.svg' else {});plt.close(fig)
    lines=['# First financial sensitivity snapshot — 2026-11-14','',
        f'Changing the text representation changes estimated portfolio risk even when prices, marginal stock variances and portfolio weights stay fixed. In this one-date retrospective snapshot, the neural settings imply annualized portfolio standard deviations of {low:.2f}%–{high:.2f}%, versus {base:.2f}% for the price-only estimate. This is sensitivity of an uncalibrated estimator, not evidence of better risk prediction or profitable returns.','',
        '![Portfolio risk estimates](figures/risk_snapshot_2026-11-14.svg)','',
        '## Fixed experiment','',
        '- Snapshot date: 2026-11-02, the pre-existing collection endpoint. Latest 252 daily proxy returns, 2025-10-31 through 2026-11-02. No evaluation window is used.',
        '- Universe and order: the same 12 companies/documents used by the audited embedding pilot; equal weights of 1/12, held fixed across settings.',
        '- Price-only covariance B: centered Ledoit–Wolf, fitted to those 252 returns.',
        '- For saved document cosine kernel K, define D = diag(sqrt(diag(B))) and C = 0.75 B + 0.25 D K D. This preserves the baseline marginal variances to floating-point precision and changes dependence.',
        '- Estimated daily portfolio variance is wᵀ C w. Annualized standard deviation is sqrt(252 × wᵀ C w). This is an annualized daily-risk convention, not a forecast of a year-long buy-and-hold outcome.',
        '- The primary 0.25 text weight, lookback and equal weights follow the existing design. The fixed supplementary grid is 0, 0.10, 0.25, 0.50, 1.00; none is selected using outcomes. Date, exact settings and contrast lists are in configs/risk_snapshot_v1.json. This is a documented exploratory specification, not formal preregistration.',
        '- Seven primary representations plus the separate E5 GPU environment diagnostic produce 40 grid rows and eight primary-weight contrasts. The GPU arm is excluded from representation-range summaries.','',
        '## Estimated portfolio risk at text weight 0.25','',
        '| Representation | Annualized estimated SD | Variance change vs price-only | Mean off-diagonal text cosine |',
        '|---|---:|---:|---:|']
    for row in primary.itertuples():
        lines.append(f'| {LABELS[row.run]} | {100*row.annualized_portfolio_sd:.2f}% | {100*row.variance_change_relative_to_price_baseline:+.2f}% | {row.mean_off_diagonal_kernel_cosine:.4f} |')
    lines += ['',f'Price-only estimated SD: **{base:.2f}%**. Every marginal stock variance remains fixed; these portfolio-risk differences arise from the dependence target.','',
        '## Which choices move the financial estimate?','',
        '| Change A → B | Portfolio variance change relative to A | Annualized SD change (percentage points) |',
        '|---|---:|---:|']
    for row in contrasts.itertuples():
        if row.run_b=='pilot_e5_192_gpu':continue
        lines.append(f'| {LABELS[row.run_a]} → {LABELS[row.run_b]} | {100*row.variance_b_relative_to_a_minus_one:+.3f}% | {row.annualized_sd_b_minus_a_percentage_points:+.4f} |')
    lines += ['',
        'The CPU/GPU environment diagnostic changes estimated variance by about −0.0000031% relative to the CPU estimate; it remains a combined hardware/software check. Chunk changes produce smaller risk shifts than the E5/Qwen family comparison here, even though peer sets also changed in the earlier text study. These are observations from one selected universe and date. They establish no general ranking of models.','',
        '## Why the large difference from price-only?','',
        'A document cosine is not an estimated return correlation. These neural document vectors have very high positive pairwise cosines, so directly inserting their raw Gram matrix as a dependence target mechanically raises co-movement and equal-weight portfolio variance in this sample. TF-IDF has a different cosine scale. Cross-model variation therefore mixes score level, common direction/anisotropy and pair-specific information. High rank stability does not guarantee calibrated financial risk estimates.','',
        'The text-weighted risk estimates are not validated as accurate. The finding motivates future training-only calibration, common-component controls, sector/factor comparators and shuffled-document checks. Such extensions must be specified and evaluated separately; they were not fitted to improve this snapshot. Larger or smaller estimated risk alone is not a benefit.','',
        '## Chronology and remaining limits','',
        'The embeddings were generated on November 3, after this November 2 price snapshot. This is explicitly retrospective mechanical integration, with no historical trade decision, approved filing-eligibility timestamps, return forecast, future realized covariance, forecast-error test, optimized holdings, turnover or transaction-cost result. The runner verifies source acceptance precedes the snapshot, but does not convert that check into approved trading eligibility. Unknown model-training cutoffs remain unresolved.',
        '',
        'Inputs are Yahoo adjusted-price proxies with vendor-scoped aliases and revised histories, not CRSP permanent-security total returns. The XOM predecessor/successor link, provider actions, retained extreme observations and identity-review scope are documented in reports/market_audit_2026-11-14.md. No raw prices or per-day returns are published. The original review statuses are preserved. The protocol’s stricter gates continue to apply before historical outcome evaluation.',
        '',
        '## Reproduce','',
        'From the repository root, with the existing market extra installed:',
        '',
        '```powershell',
        r'.\.venv\Scripts\python.exe scripts\run_risk_snapshot.py',
        '```',
        '',
        'The default output is runs/risk_snapshot_v1 and must not already exist. It re-audits local market files without downloading or invoking any embedding model; a CPU is sufficient. Aggregate reference results are in results/risk_snapshot_2026-11-14/. The receipt records exact data, config, code hashes and runtime versions. To regenerate the figure/report, install the report extra and run scripts/render_risk_snapshot.py. Small floating-point differences across runtime versions are possible.','',
        'Next substantive test: whether any text augmentation improves error against future realized risk, under explicit eligibility and outcome-window rules. That test has not run.']
    Path(report).write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',default='results/risk_snapshot_2026-11-14')
    p.add_argument('--report',default='reports/risk_snapshot_2026-11-14.md')
    p.add_argument('--figure',default='reports/figures/risk_snapshot_2026-11-14.svg')
    a=p.parse_args();render(a.results,a.report,a.figure)


if __name__=='__main__':main()
