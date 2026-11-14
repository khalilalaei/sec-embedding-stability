"""Build the two-page faculty progress brief. Requires reportlab (document tooling)."""
from pathlib import Path
import argparse
import csv
import json
import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak

ROOT=Path(__file__).resolve().parents[1]
NAVY=colors.HexColor('#15364b');TEAL=colors.HexColor('#21796f');LIGHT=colors.HexColor('#edf4f7');GRAY=colors.HexColor('#536471')


def build(output,font_regular=None,font_bold=None):
    if font_regular is None or font_bold is None:
        pairs=[(Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')),
            (Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/arial.ttf',Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/arialbd.ttf')]
        available=next(((a,b) for a,b in pairs if a.is_file() and b.is_file()),None)
        if available is None:raise ValueError('Provide --font-regular and --font-bold TTF files')
        font_regular,font_bold=available
    pdfmetrics.registerFont(TTFont('ResearchSans',str(font_regular)))
    pdfmetrics.registerFont(TTFont('ResearchSans-Bold',str(font_bold)))
    pdfmetrics.registerFontFamily('ResearchSans',normal='ResearchSans',bold='ResearchSans-Bold')
    rows=list(csv.DictReader((ROOT/'results/risk_calibration_2026-11-14/aggregate_losses.csv').open()))
    calibrated=[r for r in rows if r['kind']=='calibrated_cosine' and r['arm_role']=='primary']
    diagonal=next(r for r in rows if r['kind']=='diagonal_target')
    cov_gain=[100*float(r['covariance_entry_mse_improvement_vs_price_only']) for r in calibrated]
    header=json.loads((ROOT/'results/history_headers_audit_2026-11-14/audit_receipt.json').read_text())
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleMain',fontName='ResearchSans-Bold',fontSize=23,leading=26,textColor=NAVY,spaceAfter=6))
    styles.add(ParagraphStyle(name='Head',fontName='ResearchSans-Bold',fontSize=11.7,leading=14,textColor=NAVY,spaceBefore=11,spaceAfter=5))
    styles.add(ParagraphStyle(name='Copy',fontName='ResearchSans',fontSize=9.0,leading=12.2,textColor=colors.HexColor('#21313c'),spaceAfter=5))
    styles.add(ParagraphStyle(name='SmallCopy',fontName='ResearchSans',fontSize=7.2,leading=9.5,textColor=GRAY,spaceAfter=4))
    styles.add(ParagraphStyle(name='TableCopy',fontName='ResearchSans',fontSize=8.35,leading=11.0,textColor=colors.HexColor('#21313c')))
    styles.add(ParagraphStyle(name='WhiteHead',fontName='ResearchSans-Bold',fontSize=8.4,leading=10.8,textColor=colors.white))
    styles.add(ParagraphStyle(name='Callout',fontName='ResearchSans-Bold',fontSize=10.5,leading=14,textColor=NAVY))
    p=lambda text,style='Copy':Paragraph(text,styles[style])
    flow=[]
    def add(text,style='Copy'):flow.append(p(text,style))
    def table(data,widths,header_row=True):
        content=[[p(str(cell),'WhiteHead' if header_row and i==0 else 'TableCopy') for cell in row] for i,row in enumerate(data)]
        t=Table(content,colWidths=widths,hAlign='LEFT',repeatRows=1 if header_row else 0)
        commands=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#d8e2e8'))]
        if header_row:commands+=[('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f8fa')])]
        t.setStyle(TableStyle(commands));flow.append(t)
    add('SEC filing embeddings','TitleMain')
    add('Research progress and scale-up plan | Khalil Alaei | UCLA | November 14, 2026','SmallCopy')
    call=Table([[p('Ready for a faculty progress discussion today.<br/>A scaled empirical validation study is still in progress.','Callout')]],colWidths=[524])
    call.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),LIGHT),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#ccdfe7')),('LEFTPADDING',(0,0),(-1,-1),11),('RIGHTPADDING',(0,0),(-1,-1),11),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]));flow.append(call);flow.append(Spacer(1,9))
    table([['12 sections embedded','3 risk-loss blocks',f"{header['records_reproduced']} headers audited",'105 software tests']],[131,131,131,131],False)
    add('What has been completed','Head')
    add('An independent, reproducible pilot uses 12 real Item 1A Risk Factors sections, pinned E5/BGE/Qwen models at 192 and 320 total-token budgets, and a TF-IDF baseline. Saved source hashes, section maps, configurations and outputs support reproduction. A CPU/GPU environment check is separate from the model comparisons.')
    add('The historical expansion now contains 143 original 10-K metadata records and verified headers across the same 12 CIKs. Their full text has not yet been extracted into an expanded admitted corpus or embedded. Header/API clocks agree under an explicit Eastern-time interpretation; public-availability and execution approval remain pending.')
    add('Findings worth discussing now','Head')
    table([['Question','Pilot evidence'],
        ['Are peers stable?','Neural-family similarity ranks agree strongly (Spearman about 0.968-0.984), but only 79.2%-87.5% of directed top-2 peer memberships persist. High rank agreement does not guarantee identical peer groups.'],
        ['Does raw cosine help risk accuracy?','At the fixed 25% blend weight, raw neural targets have about 47-64 times the price-only portfolio variance squared error over three inspected 21-session blocks. This concerns this mapping and sample.'],
        ['Does calibration establish text value?',f'Past-only calibration lowers covariance-entry error by {min(cov_gain):.2f}%-{max(cov_gain):.2f}% versus the original baseline. Extra diagonal shrinkage with no text lowers it by {100*float(diagonal["covariance_entry_mse_improvement_vs_price_only"]):.2f}% and portfolio error by {100*float(diagonal["portfolio_variance_squared_error_improvement_vs_price_only"]):.2f}%; every calibrated text setting loses to that control on both aggregate metrics.']],[115,409])
    add('Current research conclusion','Head')
    add('<b>Embedding choices affect peer and risk quantities; incremental financial value from text has not been demonstrated.</b> The adverse/null results are useful evidence about calibration and baseline choice. A credible research result can be negative.')
    add('Limits that must remain visible','Head')
    add('The evidence uses 12 selected firms and three risk windows. Text checks were AI-assisted, without an independent human corpus audit. Unknown model training cutoffs, postdated embeddings, revised Yahoo price proxies and pending security links prevent historical forecasting claims. These inspected windows are development data. Software tests do not provide statistical significance.')
    add('Evidence: github.com/khalilalaei/sec-embedding-stability - pilot stability, risk accuracy, calibration and uploaded-header audit reports. Full plan: reports/RESEARCH_READINESS_2026-11-14.md.','SmallCopy')
    flow.append(PageBreak())
    add('Scope, milestones and timing','TitleMain')
    add('Proposed targets for a stronger undergraduate empirical study, subject to faculty agreement. These are planning targets, not formal UCLA minimums.','SmallCopy')
    table([['Dimension','Now','Proposed main-study target'],
        ['Cross-section','12 selected companies','About 100-200 companies across industries, with documented inclusion and historical identity rules.'],
        ['Text panel','12 embedded sections; 143 inventoried filings','About 800-2,000 source-checked annual sections over 8-10 years, with documented exclusions.'],
        ['Evaluation','3 inspected 21-session blocks','Roughly 100+ date blocks over the longer panel; eligible text at each date and explicit dependence-aware uncertainty.']],[83,151,290])
    add('Conditional working plan','Head')
    table([['Stage','Working calendar','Reviewable result'],
        ['Source bridge','Week 1, possibly into week 2','143-filing download/extraction ledger; all flags reviewed; stratified independent human spot checks.'],
        ['Scope and access','Weeks 1-2, in parallel','Frozen cohort/evaluation rules; return/security data plan; a measured GPU throughput benchmark.'],
        ['Expanded panel','Weeks 2-4','Audited corpus and return panel for the agreed scope; pinned embedding runs.'],
        ['Comparisons','Weeks 4-6','Price, diagonal, constant-correlation, industry/factor and text controls; frozen primary metrics and uncertainty analysis.'],
        ['Research delivery','Weeks 6-8','Independent reproduction/review; report or poster with figures, exclusions, limitations and retained null results.']],[92,121,311])
    add('How much longer?','Head')
    add('<b>Budget about 4-8 more weeks</b> for the scoped empirical package, assuming roughly 10-15 focused hours per week, timely faculty feedback and usable data/compute access. The planning work budget is around 60-100 hours plus unattended compute and access delays; lower availability or data exceptions can extend the calendar. A 12-firm longitudinal bridge could be ready in about 1-2 weeks. This progress brief is ready now.')
    add('What makes the next result stronger','Head')
    add('<b>Sample:</b> a justified historical cohort and security links, rather than an undocumented survivor sample. <b>Controls:</b> industry/factor and stronger price-only estimators. <b>Evaluation:</b> lock a separately uninspected panel before running; preserve the current windows as development data. <b>Timing:</b> investigate checkpoint release/training evidence and consider a prospective frozen arm. <b>Inference:</b> account for time and firm dependence; report all prespecified results.')
    add('Compute and access','Head')
    add('GPU access accelerates inference; benchmark the actual models before quoting runtime for thousands of filings. WRDS-quality security/return data improves the data layer. Neither access nor queue time is assumed in the estimate. The original full S&amp;P 500 ambition is a separate larger scope, on the order of 5,000 constituent company-years per decade; plan it after the initial scale benchmark. Publication timing cannot be promised.')
    add('Hoffman2 accounts require eligible UCLA faculty/researcher sponsorship; requests are managed at sim.idre.ucla.edu. Official access/data links and full assumptions are in the companion roadmap.','SmallCopy')
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#d3e0e6'));canvas.line(44,32,568,32)
        canvas.setFont('ResearchSans',7);canvas.setFillColor(GRAY)
        canvas.drawString(44,21,'Khalil Alaei | Faculty discussion brief | Exploratory research, not validated trading performance')
        canvas.drawRightString(568,21,str(doc.page))
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(output),pagesize=letter,leftMargin=44,rightMargin=44,topMargin=35,bottomMargin=44,
        title='SEC Filing Embeddings: Research Progress and Scale-Up Plan',author='Khalil Alaei').build(flow,onFirstPage=footer,onLaterPages=footer)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default=str(ROOT/'reports/research_progress_brief_2026-11-14.pdf'))
    p.add_argument('--font-regular');p.add_argument('--font-bold');a=p.parse_args()
    build(a.output,a.font_regular,a.font_bold)
