"""Deterministic, source-mapped Item 1A extraction. Requires optional lxml extra.

No network calls or economic inference. Character offsets refer to generated
visible text, NOT raw HTML bytes. Original DOM XPath and source lines are kept.
"""
from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re

VERSION = "item1a-dom-v1"
BLOCK = {'p','div','section','article','header','footer','li','ul','ol','tr','table',
         'h1','h2','h3','h4','h5','h6','br','hr'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def visible_document(raw):
    from lxml import html
    root = html.fromstring(raw)
    tree = root.getroottree()
    fragments, pieces, length = [], [], 0
    excluded = Counter()

    def append(value, element=None, kind=None):
        nonlocal length
        if not value:
            return
        if element is not None:
            # Whitespace normalization only; no changes to words or numbers.
            value = re.sub(r'\s+', ' ', value)
            fragments.append({'start': length, 'end': length+len(value),
                              'xpath': tree.getpath(element), 'field': kind,
                              'html_source_line': element.sourceline})
        pieces.append(value)
        length += len(value)

    def walk(element):
        if not isinstance(element.tag, str):
            return
        tag = element.tag.lower().split('}')[-1].split(':')[-1]
        style = re.sub(r'\s+', '', element.get('style','').lower())
        reason = None
        if tag in {'script','style','head','hidden'}:
            reason = 'nonvisible_tag:'+tag
        elif 'display:none' in style or 'visibility:hidden' in style or element.get('hidden') is not None:
            reason = 'hidden_attribute_or_inline_style'
        if reason:
            excluded[reason] += 1
            return
        if tag in BLOCK:
            append('\n')
        append(element.text, element, 'text')
        for child in element:
            walk(child)
            append(child.tail, child, 'tail')
        if tag in BLOCK:
            append('\n')
        elif tag in {'td','th'}:
            append(' ')
    walk(root)
    tape = ''.join(pieces)
    lines = []
    pos = 0
    for rawline in tape.splitlines(keepends=True):
        value = re.sub(r'\s+', ' ', rawline).strip()
        if value:
            lines.append({'text': value, 'visible_start':pos, 'visible_end':pos+len(rawline.rstrip('\r\n'))})
        pos += len(rawline)
    return tape, lines, fragments, dict(excluded)


def heading_at(lines, index, item):
    value = lines[index]['text']
    title = 'risk factors' if item == 'A' else 'unresolved staff comments'
    stem = rf'item\s*1\s*{item}\s*\.?\s*'
    if re.fullmatch(stem+title+r'\.?', value, re.I):
        return index
    if re.fullmatch(stem, value, re.I) and index+1 < len(lines):
        if re.fullmatch(title+r'\.?', lines[index+1]['text'], re.I):
            return index+1
    return None


def find_section(lines):
    candidates = []
    rejected = []
    for i in range(len(lines)):
        heading_end = heading_at(lines, i, 'A')
        if heading_end is None:
            continue
        end = next((j for j in range(heading_end+1, len(lines)) if heading_at(lines,j,'B') is not None), None)
        if end is None:
            rejected.append({'start_line':i, 'reason':'no_following_Item_1B'})
            continue
        n = sum(len(line['text'])+1 for line in lines[i:end])
        candidate = {'start_line':i,'heading_end_line':heading_end,'end_line':end,'candidate_characters':n}
        # Deliberately conservative pilot gate, not a universal 10-K rule.
        if n < 5000:
            rejected.append({**candidate, 'reason':'short_span_likely_table_of_contents'})
        else:
            candidates.append(candidate)
    if len(candidates) != 1:
        raise ValueError(f'Expected one unambiguous long Item 1A -> Item 1B span, got {len(candidates)}')
    return candidates[0], rejected


def artifact_reason(text, counts):
    if re.fullmatch(r'\d{1,3}', text):
        return 'standalone_page_number'
    if re.fullmatch(r'(?:financial )?table of contents|index to financial statements', text, re.I):
        return 'navigation_label'
    if re.fullmatch(r'parts?\s+i(?:\s+and\s+ii)?',text,re.I):
        return 'running_part_header'
    if re.fullmatch(r'item\s+1[a-c](?:,\s*1[a-c])*',text,re.I):
        return 'running_item_header'
    if re.fullmatch(r'(?:bank of america\s+\d{1,3}|\d{1,3}\s+bank of america)',text,re.I):
        return 'company_page_footer'
    if text == 'TARGET CORPORATION' and counts[text] > 1:
        return 'repeated_company_footer'
    if re.fullmatch(r'\d{4} (?:annual report|form 10-k)',text,re.I) and counts[text] > 1:
        return 'repeated_report_footer'
    if text == 'RISK FACTORS' and counts[text] > 2:
        return 'repeated_section_header'
    if text == 'RISK FACTORS & UNRESOLVED STAFF COMMENTS':
        return 'running_section_header'
    return None


def extract(raw):
    tape, lines, fragments, excluded = visible_document(raw)
    bounds, rejected = find_section(lines)
    start, end = bounds['start_line'], bounds['end_line']
    counts = Counter(line['text'] for line in lines[start:end])
    retained, removed = [], []
    textpieces = []
    offset = 0
    for i in range(start, end):
        line = lines[i]
        reason = artifact_reason(line['text'], counts) if i > bounds['heading_end_line'] else None
        if reason:
            removed.append({'line_index':i, **line, 'reason':reason})
            continue
        # Preserve separate visible paragraphs. No general deduplication or summarization.
        value = line['text']
        retained.append({'line_index':i, 'output_start':offset,'output_end':offset+len(value),**line})
        textpieces.append(value)
        offset += len(value)+2
    text = '\n\n'.join(textpieces)+'\n'
    # Keep the mapping fragments intersecting the selected raw visible span.
    lo, hi = lines[start]['visible_start'], lines[end]['visible_start']
    mapping = [fragment for fragment in fragments if fragment['end'] > lo and fragment['start'] < hi]
    return text, {
        'extractor_version':VERSION,
        'offset_units':'zero-based Unicode characters, end exclusive; visible offsets are not HTML byte offsets',
        'boundary':bounds,
        'start_heading':lines[start]['text'],
        'start_context':[x['text'] for x in lines[start:start+4]],
        'last_retained_line':retained[-1]['text'],
        'following_heading':lines[end]['text'],
        'following_context':[x['text'] for x in lines[end:end+3]],
        'rejected_candidates':rejected,
        'hidden_elements_excluded':excluded,
        'cleaning_counts':dict(Counter(row['reason'] for row in removed)),
        'removed_lines':removed,
        'retained_lines':retained,
        'source_fragments':mapping,
        'visible_document_sha256':hashlib.sha256(tape.encode('utf-8')).hexdigest(),
        'characters':len(text),'words':len(text.split()),
        'limitations':[
            'Parser-visible text, not a browser screenshot or a PDF layout audit.',
            'CSS visibility handling covers explicit hidden tags/attributes and inline styles, not external CSS.',
            'Standalone 1-3 digit lines treated as page numbers in this pilot; removed values must be checked.',
            'No general deduplication: section summaries and repeated substantive risk disclosures remain.',
            'Cross-referenced material outside Item 1A is not fetched or appended.'
        ]
    }


def batch(source_manifest, output_root):
    source_manifest = Path(source_manifest)
    project = source_manifest.parent.parent
    output_root = Path(output_root)
    if output_root.exists():
        raise ValueError('Output directory exists; use a new version rather than overwrite evidence')
    output_root.mkdir(parents=True)
    records = json.loads(source_manifest.read_text(encoding='utf-8-sig'))
    corpus, summary = [], []
    for r in records:
        source = project / r['raw_path']
        if digest(source) != r['raw_sha256']:
            raise ValueError('Raw source hash mismatch: '+r['ticker'])
        submission = project/r['submissions_path']
        if digest(submission) != r['submissions_sha256']:
            raise ValueError('SEC metadata hash mismatch: '+r['ticker'])
        text, evidence = extract(source.read_bytes())
        target = output_root/'data'/'text'/'extracted_v1'/f"{r['ticker']}_item1a.txt"
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(text,encoding='utf-8',newline='\n')
        relative = target.relative_to(output_root).as_posix()
        evidence.update(ticker=r['ticker'],document_id=r['document_id'],raw_path=r['raw_path'],
                        raw_sha256=r['raw_sha256'],text_path=relative,text_sha256=digest(target),
                        parser='lxml '+importlib.metadata.version('lxml'),
                        extracted_at=datetime.now(timezone.utc).isoformat())
        proof = output_root/'data'/'extraction_v1'/f"{r['ticker']}_source_map.json"
        save(proof,evidence)
        # Extracted is a distinct state: never relabel machine checks as user review.
        row = {**r,'text_path':relative,'text_sha256':digest(target),
               'review_status':'extracted_pending_review','extraction_version':VERSION,
               'source_map_path':proof.relative_to(output_root).as_posix(),
               'source_map_sha256':digest(proof),
               'review_notes':'Machine-selected boundary and cleanup; inspect extraction report before approval.'}
        corpus.append(row)
        summary.append({key:evidence[key] for key in ['ticker','document_id','characters','words','start_heading','following_heading','cleaning_counts','text_sha256']})
    save(output_root/'data'/'corpus_extracted_v1.pending.json',corpus)
    save(output_root/'data'/'extraction_v1'/'summary.json',summary)
    return corpus,summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',default='data/filings.json')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    _,summary=batch(args.manifest,args.output)
    for r in summary:
        print(r['ticker'],r['words'],'words; next heading:',r['following_heading'])


if __name__=='__main__':
    main()
