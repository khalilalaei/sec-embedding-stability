"""Offline audit and sanitized metric export for a secstab pilot-results ZIP.

Recomputes comparisons from saved similarity matrices. With --source-project,
checks original source, text, maps and chunk spans. Does not rerun inference.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile

import numpy as np
from scipy import sparse
from scipy.stats import spearmanr


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path,obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def safe(root,relative):
    relative=str(relative).replace('\\','/')
    path=(Path(root)/relative).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Path escapes archive/source root: '+relative)
    return path


def unpack(archive,output):
    with zipfile.ZipFile(archive) as z:
        if sum(i.file_size for i in z.infolist()) > 500_000_000:
            raise ValueError('Archive exceeds audit size cap')
        names=set()
        for info in z.infolist():
            key=info.filename.replace('\\','/')
            if key in names:
                raise ValueError('Duplicate archive path')
            names.add(key)
            target=safe(output,key)
            if info.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(z.read(info))


def ranked_peers(s,k=2):
    # Python sorting provides a separate implementation from secstab.core.
    rankings=[sorted((j for j in range(len(s)) if j!=i),key=lambda j:(-float(s[i,j]),j)) for i in range(len(s))]
    selected=[r[:k] for r in rankings]
    margin=[float(s[i,r[k-1]]-s[i,r[k]]) for i,r in enumerate(rankings)]
    return selected,margin


def recompute_comparison(a,b,ids,k=2):
    pa,ma=ranked_peers(a,k);pb,mb=ranked_peers(b,k)
    u=np.triu_indices(len(ids),1)
    rho=float(spearmanr(a[u],b[u]).statistic)
    rows=[]
    for i,document_id in enumerate(ids):
        x,y=set(pa[i]),set(pb[i])
        rows.append({'document_id':document_id,'overlap':len(x&y)/k,'jaccard':len(x&y)/len(x|y),
                     'margin_a':ma[i],'margin_b':mb[i],
                     'peers_a':[ids[j] for j in pa[i]],'peers_b':[ids[j] for j in pb[i]]})
    return {'spearman_pair_similarity':rho,'mean_top_k_overlap':float(np.mean([r['overlap'] for r in rows])),
            'mean_top_k_jaccard':float(np.mean([r['jaccard'] for r in rows])),
            'mean_absolute_similarity_change':float(np.mean(np.abs(a[u]-b[u]))),'companies':rows}


def check_comparison(saved,actual):
    for key in ['spearman_pair_similarity','mean_top_k_overlap','mean_top_k_jaccard','mean_absolute_similarity_change']:
        if not np.isclose(saved[key],actual[key],rtol=0,atol=1e-12):
            raise ValueError('Comparison mismatch: '+key)
    if len(saved['companies'])!=len(actual['companies']):raise ValueError('Company count mismatch')
    for a,b in zip(saved['companies'],actual['companies']):
        for key in ['document_id','peers_a','peers_b']:
            if a[key]!=b[key]:raise ValueError('Peer mismatch: '+key)
        for key in ['overlap','jaccard','margin_a','margin_b']:
            if not np.isclose(a[key],b[key],rtol=0,atol=1e-12):raise ValueError('Peer metric mismatch: '+key)


def validate_chunk_contrasts(runmeta,runtime_signatures):
    project_metadata_changes=[]
    for baseline,changed in [('pilot_e5_192','pilot_e5_320'),('pilot_bge_192','pilot_bge_320'),('pilot_qwen_192_gpu','pilot_qwen_320_gpu')]:
        if changed not in runmeta:continue
        a=runmeta[baseline];b=runmeta[changed]
        config_a={k:v for k,v in a['settings'].items() if k!='total_token_budget'}
        config_b={k:v for k,v in b['settings'].items() if k!='total_token_budget'}
        python_a,packages_a=runtime_signatures[baseline]
        python_b,packages_b=runtime_signatures[changed]
        third_party_a={k:v for k,v in packages_a.items() if k.lower()!='sec-embedding-stability'}
        third_party_b={k:v for k,v in packages_b.items() if k.lower()!='sec-embedding-stability'}
        if packages_a.get('sec-embedding-stability')!=packages_b.get('sec-embedding-stability'):
            project_metadata_changes.append({'run_a':baseline,'run_b':changed,
                'project_version_a':packages_a.get('sec-embedding-stability'),
                'project_version_b':packages_b.get('sec-embedding-stability'),
                'requirement':'Check inference source equality across recorded commits before interpreting as budget-only.'})
        if config_a!=config_b or a['batch_size']!=b['batch_size'] or python_a!=python_b or third_party_a!=third_party_b:
            raise ValueError('Chunk contrast has an additional configuration/environment change: '+changed)
    return project_metadata_changes


def lexical_matrix(texts,saved):
    # Recompute TF, DF, IDF and normalization from source text; no saved vectors used.
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    pattern=re.compile(r'(?u)\b\w\w+\b')
    counts=[]
    for text in texts:
        tokens=[x for x in pattern.findall(text.lower()) if x not in ENGLISH_STOP_WORDS]
        terms=tokens+[' '.join(pair) for pair in zip(tokens,tokens[1:])]
        counts.append(Counter(terms))
    vocabulary=sorted(set().union(*(c.keys() for c in counts)))
    index={word:i for i,word in enumerate(vocabulary)}
    if index!=saved['vocabulary']:raise ValueError('Rebuilt TF-IDF vocabulary differs')
    df=np.array([sum(word in count for count in counts) for word in vocabulary])
    idf=np.log((1+len(texts))/(1+df))+1
    np.testing.assert_allclose(idf,saved['idf'],rtol=0,atol=1e-12)
    rows,cols,values=[],[],[]
    for i,count in enumerate(counts):
        for term,freq in count.items():
            j=index[term];rows.append(i);cols.append(j);values.append((1+np.log(freq))*idf[j])
    x=sparse.csr_matrix((values,(rows,cols)),shape=(len(texts),len(index)))
    norms=np.sqrt(x.multiply(x).sum(axis=1)).A1
    x=sparse.diags(1/norms)@x
    return (x@x.T).toarray(),len(index)


def audit(input_root,archive_hash,source_root=None):
    root=Path(input_root)
    corpus=read(root/'corpus_extracted_v1.json')
    ids=[r['document_id'] for r in corpus]
    if len(ids)!=12 or len(set(ids))!=12:raise ValueError('Expected 12 unique filings')
    names={r['document_id']:r['ticker'] for r in corpus}
    lock=read(root/'models.lock.json')
    matrices={};runmeta={};runtime_signatures={};hash_checks=0;source_checks=set();texts=None;chunk_sets={}
    if source_root is not None:
        source_root=Path(source_root)
        texts=[]
        for r in corpus:
            for kind in ['raw','submissions','text','source_map','review_report']:
                path=safe(source_root,r[kind+'_path'])
                if sha(path)!=r[kind+'_sha256']:raise ValueError('Original/source artifact hash mismatch: '+r['ticker']+' '+kind)
                source_checks.add(path.relative_to(source_root).as_posix())
            texts.append(safe(source_root,r['text_path']).read_text(encoding='utf-8'))
    for directory in sorted((root/'runs').iterdir()):
        if not directory.is_dir():continue
        m=read(directory/'manifest.json')
        if m['status']!='complete' or m['document_order']!=ids or m['corpus_sha256']!=sha(root/'corpus_extracted_v1.json'):
            raise ValueError('Run corpus/status mismatch: '+directory.name)
        if read(directory/'corpus_snapshot.json')!=corpus:raise ValueError('Snapshot differs')
        # GPU runs recorded only the untracked GPU environment, not tracked edits.
        if any(not line.startswith('?? ') for line in m['git_status'].splitlines()):
            raise ValueError('Tracked working-tree changes need explicit source audit')
        for relative,expected in m['outputs'].items():
            if sha(safe(directory,relative))!=expected:raise ValueError('Run output hash mismatch')
            hash_checks+=1
        s=np.load(directory/'similarity.npy',allow_pickle=False)
        if s.shape!=(12,12) or not np.isfinite(s).all():raise ValueError('Invalid matrix')
        np.testing.assert_allclose(s,s.T,rtol=0,atol=1e-12)
        np.testing.assert_allclose(np.diag(s),1,rtol=0,atol=1e-12)
        chosen,margins=ranked_peers(s)
        saved_peers=read(directory/'peers.json')
        for i,row in enumerate(saved_peers):
            if row['document_id']!=ids[i] or row['peers']!=[ids[j] for j in chosen[i]]:raise ValueError('Saved peer mismatch')
            np.testing.assert_allclose(row['boundary_margin'],margins[i],rtol=0,atol=1e-12)
        meta={'run_id':directory.name,'git_commit':m['git_commit'],'manifest_sha256':sha(directory/'manifest.json'),
              'outputs':m['outputs'],'started_at':m['started_at'],'completed_at':m['completed_at'],
              'packages':{k:v for k,v in m['packages'].items() if k.lower() in {'numpy','scipy','scikit-learn','torch','transformers','sentence-transformers','sec-embedding-stability'}},
              'git_tracked_changes':False,'untracked_gpu_environment_recorded':bool(m['git_status']),
              'document_count':12,'pair_count':66,
              'similarity_min_off_diagonal':float(s[np.triu_indices(12,1)].min()),
              'similarity_max_off_diagonal':float(s[np.triu_indices(12,1)].max())}
        if (directory/'embedding_settings.json').exists():
            z=np.load(directory/'embeddings.npy',allow_pickle=False)
            if z.shape[0]!=12 or not np.isfinite(z).all():raise ValueError('Invalid embeddings')
            np.testing.assert_allclose(np.linalg.norm(z,axis=1),1,rtol=0,atol=1e-12)
            np.testing.assert_allclose(z@z.T,s,rtol=0,atol=2e-12)
            if read(directory/'models_snapshot.json')!=lock:raise ValueError('Model lock differs')
            settings=read(directory/'embedding_settings.json')
            if settings['model'] not in lock['models']:raise ValueError('Selected model differs')
            chunks=read(directory/'chunks.json');chunk_sets[directory.name]=chunks
            if texts is not None:
                for doc,text in zip(ids,texts):
                    spans=[c for c in chunks if c['document_id']==doc];cursor=0
                    for c in spans:
                        a,b=c['start_char'],c['end_char']
                        if a!=cursor or b<=a or b>len(text):raise ValueError('Chunk coverage gap/overlap')
                        if hashlib.sha256(text[a:b].encode()).hexdigest()!=c['span_sha256']:raise ValueError('Chunk source hash mismatch')
                        cursor=b
                    if cursor!=len(text):raise ValueError('Incomplete source coverage')
            if any(c['document_id'] not in ids for c in chunks):raise ValueError('Unexpected chunk ID')
            batch_size=int(m['command'][m['command'].index('--batch-size')+1]) if '--batch-size' in m['command'] else 8
            meta.update(settings=settings,batch_size=batch_size,vector_shape=list(z.shape),vector_storage_dtype=str(z.dtype),chunk_count=len(chunks),
                        chunk_count_by_ticker=dict(Counter(names[c['document_id']] for c in chunks)),
                        gram_matrix_max_absolute_error=float(np.max(np.abs(z@z.T-s))))
        elif texts is not None:
            rebuilt,vocab=lexical_matrix(texts,read(directory/'tfidf.json'))
            np.testing.assert_allclose(rebuilt,s,rtol=0,atol=2e-12)
            meta.update(tfidf_recomputed_from_text=True,vocabulary_size=vocab,tfidf_max_absolute_error=float(np.max(np.abs(rebuilt-s))))
        matrices[directory.name]=s;runmeta[directory.name]=meta
        runtime_signatures[directory.name]=(m['python'],m['packages'])
    shared=[name for name,m in runmeta.items() if m.get('settings',{}).get('total_token_budget')==192]
    if any(chunk_sets[name]!=chunk_sets[shared[0]] for name in shared):raise ValueError('192-token source spans differ')
    shared320=[name for name,m in runmeta.items() if m.get('settings',{}).get('total_token_budget')==320]
    if any(chunk_sets[name]!=chunk_sets[shared320[0]] for name in shared320):raise ValueError('320-token source spans differ')
    project_metadata_changes=validate_chunk_contrasts(runmeta,runtime_signatures)
    comparisons=[];comparison_checks=0
    for path in sorted((root/'runs').glob('*.json')):
        saved=read(path)
        a=PurePosixPath(saved['run_a'].replace('\\','/')).name
        b=PurePosixPath(saved['run_b'].replace('\\','/')).name
        if saved['manifest_a_sha256']!=runmeta[a]['manifest_sha256'] or saved['manifest_b_sha256']!=runmeta[b]['manifest_sha256']:
            raise ValueError('Comparison manifest hash mismatch')
        actual=recompute_comparison(matrices[a],matrices[b],ids)
        check_comparison(saved,actual);comparison_checks+=1
        for row in actual['companies']:
            row.update(ticker=names[row['document_id']],peers_a_tickers=[names[x] for x in row['peers_a']],peers_b_tickers=[names[x] for x in row['peers_b']],
                       set_changed=set(row['peers_a'])!=set(row['peers_b']),order_changed=row['peers_a']!=row['peers_b'],
                       closest_peer_changed=row['peers_a'][0]!=row['peers_b'][0])
        actual.update(comparison_id=path.stem,run_a=a,run_b=b,
                      changed_peer_sets=sum(r['set_changed'] for r in actual['companies']),
                      changed_closest_peers=sum(r['closest_peer_changed'] for r in actual['companies']),
                      changed_peer_orders=sum(r['order_changed'] for r in actual['companies']),
                      retained_memberships=sum(len(set(r['peers_a'])&set(r['peers_b'])) for r in actual['companies']),
                      comparison_sha256=sha(path))
        comparisons.append(actual)
    baseline_runs={'pilot_tfidf','pilot_e5_192','pilot_e5_320','pilot_e5_192_gpu','pilot_bge_192','pilot_qwen_192_gpu'}
    baseline_comparisons={'tfidf_vs_e5_192','e5_192_vs_320','e5_cpu_vs_gpu_192','e5_vs_bge_192','e5_vs_qwen_192_gpu','bge_vs_qwen_192'}
    complete_runs=baseline_runs|{'pilot_bge_320','pilot_qwen_320_gpu'}
    complete_comparisons=baseline_comparisons|{'bge_192_vs_320','qwen_192_vs_320_gpu'}
    actual_comparisons={c['comparison_id'] for c in comparisons}
    if not ((set(runmeta)==baseline_runs and actual_comparisons==baseline_comparisons) or
            (set(runmeta)==complete_runs and actual_comparisons==complete_comparisons)):
        raise ValueError('Expected either the frozen initial pilot or the complete model/chunk pilot')
    return {'scope':'descriptive 12-company pilot; no finance/backtest/inference rerun',
            'input_archive_sha256':archive_hash,'corpus_sha256':sha(root/'corpus_extracted_v1.json'),
            'model_lock_sha256':sha(root/'models.lock.json'),'models':lock,
            'documents':[{k:r[k] for k in ['ticker','cik','document_id','report_date','accepted_at','source_url','raw_sha256','text_sha256','source_map_sha256']} for r in corpus],
            'verification':{'run_count':len(runmeta),'comparison_count':comparison_checks,'verified_output_hashes':hash_checks,
                            'verified_source_artifacts':len(source_checks),'source_checks_enabled':source_root is not None,
                            'all_192_neural_chunk_records_identical':True,'all_320_neural_chunk_records_identical':True,
                            'initial_chunk_grid_complete':set(runmeta)==complete_runs,'chunk_inference_settings_and_third_party_environments_matched':True,
                            'project_distribution_metadata_changes':project_metadata_changes,'neural_inference_rerun':False,
                            'tokenizer_budget_recount':False,'source_span_hashes_and_coverage_checked':source_root is not None,
                            'tfidf_recomputed_from_source':texts is not None,
                            'independence':'Same assistant reviewed the saved runs; not an independent audit.'},
            'runs':runmeta,'similarities':{k:v.tolist() for k,v in matrices.items()},'comparisons':comparisons}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',required=True)
    p.add_argument('--source-project')
    p.add_argument('--output',required=True)
    args=p.parse_args()
    output=Path(args.output)
    if output.exists():raise ValueError('Output exists; choose a new evidence version')
    with tempfile.TemporaryDirectory() as temporary:
        unpack(args.archive,temporary)
        result=audit(temporary,sha(args.archive),args.source_project)
    save(output,result)
    print(json.dumps(result['verification'],indent=2))
    for c in result['comparisons']:
        print(c['comparison_id'],'rho=',c['spearman_pair_similarity'],'retained=',str(c['retained_memberships'])+'/24','changed_sets=',c['changed_peer_sets'])


if __name__=='__main__':
    main()
