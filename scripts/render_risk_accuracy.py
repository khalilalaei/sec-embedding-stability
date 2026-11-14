"""Render frozen aggregate historical risk-loss evidence (optional report extra)."""
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
    root=Path(root);summary=json.loads((root/'summary.json').read_text());windows=json.loads((root/'windows.json').read_text())
    aggregate=pd.read_csv(root/'aggregate_losses.csv');losses=pd.read_csv(root/'window_losses.csv')
    primary=aggregate[(aggregate.kernel_type=='raw_cosine')&(aggregate.arm_role=='primary')&(aggregate.text_weight==summary['primary_text_weight'])].copy()
    if len(primary)!=7 or summary['windows']!=3:raise ValueError('Unexpected frozen study shape')
    primary['portfolio_ratio']=1-primary.portfolio_variance_squared_error_improvement_vs_price_only
    primary['covariance_ratio']=1-primary.covariance_entry_mse_improvement_vs_price_only
    controls=aggregate[(aggregate.kernel_type=='score_level_control')&(aggregate.arm_role=='primary')].set_index('run').loc[primary.run]
    neural=primary[primary.run!='pilot_tfidf'];tfidf=primary[primary.run=='pilot_tfidf'].iloc[0]
    plt.rcParams['svg.hashsalt']='risk-accuracy-v1'
    colors=['#788493','#276a9d','#276a9d','#257b62','#257b62','#985281','#985281']
    fig,axes=plt.subplots(1,2,figsize=(11.6,4.8),gridspec_kw={'width_ratios':[1,1]})
    for ax,metric,control_metric,title in zip(axes,['portfolio_ratio','covariance_ratio'],['portfolio_variance_squared_error_improvement_vs_price_only','covariance_entry_mse_improvement_vs_price_only'],['Portfolio variance error','Covariance-entry error']):
        values=primary[metric].to_numpy();x=np.arange(7)
        ax.bar(x,values,color=colors,width=.65,label='Raw cosine blend')
        ax.scatter(x,1-controls[control_metric].to_numpy(),s=27,color='#141b24',marker='D',label='Score-level control',zorder=4)
        ax.axhline(1,color='#263341',linestyle='--',linewidth=1.1,label='Price-only = 1')
        ax.set_xticks(x,[LABELS[r].replace(' ','\n') for r in primary.run],fontsize=8)
        ax.set_title(title,loc='left',fontsize=12);ax.set_ylabel('Mean squared error / price-only mean squared error')
        ax.spines[['right','top']].set_visible(False);ax.set_axisbelow(True);ax.grid(axis='y',alpha=.15)
        if metric=='portfolio_ratio':
            ax.set_yscale('log');ax.set_ylim(.8,100);ax.set_yticks([1,2,5,10,20,50,100],[1,2,5,10,20,50,100])
            for xi,v in zip(x,values):ax.text(xi,v*1.10,f'{v:.1f}×',ha='center',fontsize=8)
        else:
            ax.set_ylim(0,1.95)
            for xi,v in zip(x,values):ax.text(xi,v+.07,f'{v:.2f}×',ha='center',fontsize=8)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper left',bbox_to_anchor=(.065,.925),ncol=3,frameon=False,fontsize=9)
    fig.suptitle('Subsequent-window risk accuracy: lower error ratios are better',x=.07,ha='left',fontsize=14)
    fig.text(.07,.025,'3 nonoverlapping 21-session blocks | equal weights | text weight 0.25 | exploratory retrospective study',fontsize=9)
    fig.tight_layout(rect=[0,.06,1,.86]);Path(figure).parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(figure,metadata={'Date':None} if Path(figure).suffix=='.svg' else {});plt.close(fig)
    lines=['# First subsequent-window risk accuracy test — 2026-11-14','',
        f'At the fixed 25% text weight, **{summary["primary_representations_with_lower_portfolio_error"]} of 7 primary representations reduced mean squared portfolio variance error** across three subsequent 21-session blocks. The neural blends had {neural.portfolio_ratio.min():.1f}–{neural.portfolio_ratio.max():.1f} times the price-only error. TF-IDF had {tfidf.portfolio_ratio:.2f} times the portfolio error, while reducing covariance-entry error by {100*tfidf.covariance_entry_mse_improvement_vs_price_only:.2f}%. These results concern this uncalibrated blend, selected sample, three windows and assumed timing; they do not establish that embeddings cannot improve financial models.','',
        '![Error ratios against price-only](figures/risk_accuracy_2026-11-14.svg)','',
        '## Fixed design and exact windows','',
        'The [protocol](../docs/RISK_ACCURACY_PROTOCOL.md) and [config](../configs/risk_accuracy_v1.json) were committed at `0d6d166d13d14dcda89771a61bf59b5b7627bbc8` before window-loss evaluation. This is not an untouched holdout: the earlier November snapshot already summarized returns containing these dates. No losses were used to select models, text weights or windows.','',
        '| Decision close (New York) | Trailing return dates (252) | Subsequent return dates (21) |',
        '|---|---|---|']
    for w in windows:lines.append(f'| {w["decision_date"]} | {w["train_start"]} – {w["train_end"]} | {w["test_start"]} – {w["test_end"]} |')
    lines += ['',
        'The October month-end candidate rolled back to October 30 and was excluded: only one subsequent return was available in the frozen dataset, versus 21 required. The horizon was not shortened. The three admitted evaluation windows do not overlap; their estimation windows do overlap.',
        '',
        'For the diagnostic timing assumption, each filing becomes eligible at the close of the first XNYS session strictly after its SEC acceptance local date. The latest assumed eligibility is Microsoft, July 30, 2026 at 20:00 UTC. These are explicitly assumption-only AI-assisted records, not independently approved execution eligibility. The original pending security/availability statuses were not changed.',
        '',
        'Fit centered Ledoit–Wolf covariance B to trailing returns. With D=diag(sqrt(diag(B))), use C=0.75B+0.25DKD and equal weights w=1/12. Marginal variances stay fixed. The realized daily covariance proxy is the centered sample covariance of the next 21 return vectors (ddof=1). Its portfolio proxy is wᵀS_future w, independently checked against the sample variance of the equal-weight daily return series.',
        '',
        'Primary loss is (wᵀCw − wᵀS_future w)². Secondary loss averages (C_ij − S_future,ij)² across all 144 entries; off-diagonal loss across 132 entries is also saved. Aggregate losses are equal means across the three dates. Ratios below divide each aggregate model loss by the matching aggregate price-only loss. They are error ratios, not volatility ratios or investment returns.',
        '',
        '## Primary weight results','',
        '| Representation | Portfolio error / baseline | Covariance error / baseline | Portfolio-error wins |',
        '|---|---:|---:|---:|',
        '| Price-only | 1.00× | 1.00× | Reference |']
    for r in primary.itertuples():lines.append(f'| {LABELS[r.run]} | {r.portfolio_ratio:.2f}× | {r.covariance_ratio:.3f}× | {r.portfolio_variance_squared_error_windows_better_than_price_only}/3 |')
    lines += ['',
        'The primary mean price-only portfolio variance squared error is '+f'{summary["price_only_mean_portfolio_variance_squared_error"]:.8e}'+', in daily decimal-return variance squared. Its covariance-entry MSE is '+f'{summary["price_only_mean_covariance_entry_mse"]:.8e}'+'. Error ratios can be large when the reference error is small; retain the absolute losses alongside ratios.',
        '',
        '## Did score level explain the neural result?','',
        'The supplementary control uses K_level=(1−c)I+c11ᵀ, where c is the mean off-diagonal cosine of the corresponding kernel. This preserves the model’s average score level and discards firm-specific pair structure. It remains PSD and uses the same 25% blend weight.',
        '',
        '| Representation | Full-kernel portfolio error / baseline | Score-level control / baseline |',
        '|---|---:|---:|']
    for r in primary.itertuples():
        control=1-controls.loc[r.run,'portfolio_variance_squared_error_improvement_vs_price_only']
        lines.append(f'| {LABELS[r.run]} | {r.portfolio_ratio:.2f}× | {control:.2f}× |')
    lines += ['',
        'The full neural kernels and their score-level controls have similar portfolio losses. This is consistent with the already-observed high cosine levels driving much of the increase in estimated co-movement under the direct mapping. It does not prove that company-specific semantic information is useless. Raw document cosine is not a calibrated return correlation. TF-IDF’s small covariance-error reduction and larger portfolio-error increase show why these metrics must be reported separately: the portfolio quadratic form and matrix-entry average weight errors differently.',
        '',
        '## Per-window estimated versus realized risk','',
        '| Evaluation block | Price-only annualized SD | Realized proxy annualized SD | Neural estimated SD range |',
        '|---|---:|---:|---:|']
    for w in windows:
        group=losses[losses.decision_date==w['decision_date']];b=group[group.run=='price_only'].iloc[0]
        nn=group[(group.kernel_type=='raw_cosine')&(group.arm_role=='primary')&(group.text_weight==.25)&(group.run!='pilot_tfidf')]
        def sd(v):return 100*np.sqrt(252*v)
        lines.append(f'| {w["test_start"]} – {w["test_end"]} | {sd(b.estimated_daily_portfolio_variance):.2f}% | {sd(b.realized_daily_portfolio_variance_proxy):.2f}% | {sd(nn.estimated_daily_portfolio_variance.min()):.2f}%–{sd(nn.estimated_daily_portfolio_variance.max()):.2f}% |')
    lines += ['',
        'Annualization uses sqrt(252 × daily variance). The realized value is an annualized 21-day sample proxy; it is not a realized year-long return or volatility estimate. The estimators use no subsequent-window values when fitting each baseline.',
        '',
        '## Complete evidence and limits','',
        'Saved outputs contain 147 window-loss rows (49 arms/settings per date), 49 aggregate rows, all four calendar candidates/exclusions, 12 assumption records, baseline and realized covariance matrices for all three windows, and code/config/data receipts. The fixed supplementary text-weight grid is preserved, with no winning weight selected. The E5 GPU arm is a combined environment diagnostic and is excluded from the seven primary representation counts.',
        '',
        'Only 3 blocks and 12 deliberately selected companies are available; daily rows, firm pairs and model arms are not independent replicates. No significance tests, confidence intervals or general predictive-superiority claims are made. The November embeddings postdate all evaluation windows and model training cutoffs are unknown. Yahoo revised adjusted-price histories, vendor aliases, the XOM successor assumption and unapproved historical execution eligibility remain limitations. This is an assumption-based retrospective loss diagnostic, not an absence-of-look-ahead result.',
        '',
        'Large provider observations were retained under the frozen no-deletion rule. A post-run event-context check found Oracle’s September 9, 2025 earnings announcement immediately before its September 10 price jump, and Target’s November 20, 2024 earnings announcement on its large-decline date. These issuer releases support event context only; they do not independently verify the Yahoo price magnitudes. Target’s 2024 event is outside all fitted windows. This review did not alter observations, estimators or exclusions. Sources: https://www.oracle.com/news/announcement/q1fy26-earnings-release-2025-09-09/ and https://corporate.target.com/press/release/2024/11/target-corporation-reports-third-quarter-earnings .',
        '',
        '## Reproduce locally','',
        '```powershell',r'.\.venv\Scripts\python.exe scripts\run_risk_accuracy.py','```','',
        'Requires the existing market extra, frozen local yahoo_pilot_v2 and corpus. No download, GPU, embedding inference or WRDS access is needed. The output directory runs/risk_accuracy_v1 must not already exist. Aggregate reference results are in results/risk_accuracy_2026-11-14/. The receipt records the protocol commit and exact computation/data/config hashes. The optional report extra supports scripts/render_risk_accuracy.py.',
        '',
        'The next research question is whether calibrated dependence targets and company-specific text add value beyond score-level, price and industry/factor controls on a larger independently evaluated sample. Those extensions have not run; the present null/adverse results remain part of the record.']
    Path(report).write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--results',default='results/risk_accuracy_2026-11-14')
    p.add_argument('--report',default='reports/risk_accuracy_2026-11-14.md');p.add_argument('--figure',default='reports/figures/risk_accuracy_2026-11-14.svg')
    a=p.parse_args();render(a.results,a.report,a.figure)


if __name__=='__main__':main()
