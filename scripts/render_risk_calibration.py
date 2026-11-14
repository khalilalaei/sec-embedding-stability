"""Render fixed calibration results and matched price/control comparisons."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

LABELS={'pilot_tfidf':'TF-IDF','pilot_e5_192':'E5 192','pilot_e5_320':'E5 320','pilot_bge_192':'BGE 192','pilot_bge_320':'BGE 320','pilot_qwen_192_gpu':'Qwen 192','pilot_qwen_320_gpu':'Qwen 320'}


def render(root,report,figure):
    root=Path(root);summary=json.loads((root/'summary.json').read_text())
    table=pd.read_csv(root/'aggregate_losses.csv');fits=pd.read_csv(root/'calibration_fits.csv');comparisons=pd.read_csv(root/'comparisons.csv')
    primary=table[(table.kind=='calibrated_cosine')&(table.arm_role=='primary')].copy()
    controls=table[table.kind.isin(['price_only','diagonal_target','price_constant_correlation'])].copy()
    if len(primary)!=7 or len(table)!=27 or len(fits)!=48 or summary['windows']!=3:raise ValueError('Unexpected frozen study shape')
    chart=pd.concat([controls[controls.kind!='price_only'],primary],ignore_index=True)
    names=['Extra diagonal shrinkage','Past-price constant correlation']+[LABELS[r] for r in primary.run]
    plt.rcParams['svg.hashsalt']='risk-calibration-v1'
    fig,axes=plt.subplots(1,2,figsize=(11.5,5.7),sharey=True)
    colors=['#667281','#a4adb7','#788493','#276a9d','#276a9d','#257b62','#257b62','#985281','#985281']
    metrics=['portfolio_variance_squared_error','covariance_entry_mse']
    for ax,metric,title in zip(axes,metrics,['Portfolio variance error','Covariance-entry error']):
        values=-100*chart[metric+'_improvement_vs_price_only'].to_numpy();y=np.arange(len(values))
        ax.barh(y,values,color=colors,height=.65)
        ax.axvline(0,color='#263341',linestyle='--',linewidth=1)
        ax.set_title(title,loc='left',fontsize=12);ax.set_xlabel('Mean squared error change vs price-only (%)')
        ax.set_yticks(y,names,fontsize=9);ax.spines[['top','right']].set_visible(False)
        ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
        for yi,v in zip(y,values):
            ax.annotate(f'{v:+.2f}%',(v,yi),xytext=(4 if v>=0 else -4,0),textcoords='offset points',ha='left' if v>=0 else 'right',va='center',fontsize=8)
        if metric=='portfolio_variance_squared_error':ax.set_xlim(-55,44)
        else:ax.set_xlim(-3,0.3)
    axes[0].invert_yaxis()
    fig.suptitle('Past-only calibration: compare text with text-free controls',x=.04,ha='left',fontsize=14)
    fig.text(.04,.025,'Negative = lower error | 3 previously inspected blocks | fixed blend weight 0.25 | exploratory retrospective study',fontsize=8)
    fig.tight_layout(rect=[0,.055,1,.94]);Path(figure).parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(figure,metadata={'Date':None} if Path(figure).suffix=='.svg' else {});plt.close(fig)
    diagonal=controls[controls.kind=='diagonal_target'].iloc[0];constant=controls[controls.kind=='price_constant_correlation'].iloc[0]
    covariance_improvement=100*primary.covariance_entry_mse_improvement_vs_price_only
    lines=['# Past-only shrinkage calibration — exploratory results','',
        f'Calibration sharply reduced the original raw-neural error, but **0 of 7 primary representations beat price-only portfolio variance accuracy**. All seven reduced covariance-entry error by {covariance_improvement.min():.2f}%–{covariance_improvement.max():.2f}% versus price-only. However, extra diagonal shrinkage with no text reduced covariance-entry error by {100*diagonal.covariance_entry_mse_improvement_vs_price_only:.2f}% and portfolio variance error by {100*diagonal.portfolio_variance_squared_error_improvement_vs_price_only:.2f}%, outperforming every calibrated text setting on both aggregate losses in these three blocks. An incremental benefit from text is not established.','',
        '![Calibration versus price controls](figures/risk_calibration_2026-11-14.svg)','',
        '## Fixed specification and chronology','',
        'The [protocol](../docs/RISK_CALIBRATION_PROTOCOL.md) and [config](../configs/risk_calibration_v1.json) were committed at `ab048039081292e123d297019721ba503448e5ed` before calibrated loss evaluation. This extension was designed after observing the raw-blend failures and reuses the same three inspected windows; it is method development, not fresh validation. Original raw results and their adverse findings remain unchanged.',
        '',
        'At each July 31, August 31 and September 30 decision, fit Ledoit–Wolf covariance B on 252 trailing returns and convert it to correlation R_B. For a saved document cosine matrix K, fit alpha=clip(sum_{i<j} K_ij R_B,ij / sum_{i<j} K_ij², 0, 1); a zero denominator gives zero. The target is K_cal=(1−alpha)I+alpha K. Blend C=0.75B+0.25D K_cal D with D=diag(sqrt(diag(B))). Subsequent 21-session realized risk is used only for loss evaluation.',
        '',
        'This one-parameter fit attenuates off-diagonal cosine scores and cannot amplify them or change their relative pattern. Its objective is fitting trailing price correlation, not minimizing future portfolio error. K_cal and C remain PSD, and stock marginal variances remain fixed. The pairwise fit does not treat 66 pairs as independent for inference.',
        '',
        'The blend decomposes as C=0.75B+0.25(1−alpha)diag(B)+0.25alpha D K D. Calibration therefore introduces additional diagonal shrinkage as well as rescaling text. That is why the price-only controls are necessary.',
        '',
        '## Aggregate error changes versus price-only','',
        'Negative changes below mean lower mean squared error. These are relative changes in loss, not changes in volatility or investment returns.',
        '',
        '| Estimator / control | Portfolio variance error change | Covariance-entry error change |',
        '|---|---:|---:|',
        '| Price-only | Reference | Reference |']
    labels={'diagonal_target':'Extra diagonal shrinkage (no text)','price_constant_correlation':'Past-price constant correlation (no text)'}
    for row in chart.itertuples():
        name=labels[row.kind] if row.kind in labels else LABELS[row.run]
        lines.append(f'| {name} | {-100*row.portfolio_variance_squared_error_improvement_vs_price_only:+.2f}% | {-100*row.covariance_entry_mse_improvement_vs_price_only:+.2f}% |')
    lines += ['',
        'Both controls use the same 25% blend weight. The constant-correlation target uses the mean off-diagonal trailing price correlation and contains no text. No estimator or parameter was selected using these outcomes. All per-window and absolute losses are saved alongside percentage comparisons.',
        '',
        '## Does company-specific text help after calibration?','',
        'Each raw score-level kernel receives its own coefficient fitted by the same rule. With an interior coefficient and a constant off-diagonal cosine c, alpha*c equals the mean trailing price correlation. All 48 fits were interior in this run, so all calibrated level-only targets reduce to the past-price constant-correlation control. This equality was verified numerically.',
        '',
        '| Representation | Portfolio-error improvement vs calibrated level-only | Covariance-error improvement vs calibrated level-only |',
        '|---|---:|---:|']
    paired=comparisons[(comparisons.reference=='paired_calibrated_level_control')&(comparisons.arm_role=='primary')]
    for row in paired.itertuples():
        lines.append(f'| {LABELS[row.run]} | {100*row.portfolio_variance_squared_error_improvement_vs_reference:+.3f}% | {100*row.covariance_entry_mse_improvement_vs_reference:+.3f}% |')
    lines += ['',
        'Positive improvement means the full calibrated kernel has lower error than its calibrated level-only control. Company-specific structure gives small covariance-loss improvements over that control here, while worsening portfolio variance error. The text-free diagonal target still has lower aggregate error on both metrics than every calibrated text arm. These metric-specific outcomes do not support a general text-value claim.',
        '',
        '## Fitted scale factors','',
        '| Representation | Minimum alpha | Maximum alpha |',
        '|---|---:|---:|']
    for name in primary.run:
        subset=fits[(fits.run==name)&(fits.kind=='calibrated_cosine')]
        lines.append(f'| {LABELS[name]} | {subset.alpha.min():.4f} | {subset.alpha.max():.4f} |')
    lines += ['',
        'All coefficients, unconstrained coefficients, fitting intervals, objective losses and pair counts are retained. Alpha is fitted per date rather than chosen from a future-loss grid. No best model or coefficient is selected from the report.',
        '',
        '## Evidence and limitations','',
        'Outputs contain 81 window-loss rows, 27 aggregate rows, 48 fit records and 40 comparisons (eight settings against five references). Seven settings are primary; E5 GPU is a separate environment diagnostic. Raw/reference losses reproduce the original accuracy study within floating-point tolerance. After enhancing only summary counters, unchanged numerical outputs reproduced byte-for-byte.',
        '',
        'The 12 selected firms, three reused blocks, overlapping training windows, unknown model cutoffs, November-generated embeddings, Yahoo revised adjusted-price proxies, assumed eligibility and XOM successor link have the same limitations as the earlier reports. Price information is used both by the baseline and calibration. This is not a fresh out-of-sample validation, a look-ahead-free historical forecast, a return forecast or a trading-profit result. No significance tests, confidence intervals, optimized portfolios, transaction costs or expanded-sample results were introduced.',
        '',
        'The useful finding is methodological: a gain against a single price baseline can be explained by a stronger text-free covariance control. Further development needs an independently reserved or prospective evaluation and price/industry controls; repeatedly adapting methods to these three blocks cannot establish general predictive value.',
        '',
        '## Reproduce locally','',
        '```powershell',r'.\.venv\Scripts\python.exe scripts\run_risk_calibration.py','```','',
        'Uses the existing frozen local market/corpus files and saved kernels; no GPU or download is needed. The output runs/risk_calibration_v1 must not already exist. Reference outputs and provenance are in results/risk_calibration_2026-11-14/. The report extra supports scripts/render_risk_calibration.py.']
    Path(report).write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--results',default='results/risk_calibration_2026-11-14')
    p.add_argument('--report',default='reports/risk_calibration_2026-11-14.md');p.add_argument('--figure',default='reports/figures/risk_calibration_2026-11-14.svg')
    a=p.parse_args();render(a.results,a.report,a.figure)


if __name__=='__main__':main()
