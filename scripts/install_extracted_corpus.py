"""Install hash-bound extracted text without replacing manual files or raw inputs.

Run the COPY included in the extracted package, next to checksums.json and data/.
After git pull: python PATH_TO_PACKAGE/install_extracted_corpus.py --project .
"""
import argparse
from contextlib import chdir
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confined(root, relative):
    path = (root/relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Path escapes root: '+relative)
    return path


def install(bundle, project):
    # Read source files only from the adjacent package; no remote downloads.
    bundle, project = Path(bundle).resolve(),Path(project).resolve()
    if not (project/'pyproject.toml').is_file():
        raise ValueError('Run in the project folder or pass --project with its path')
    import secstab
    if tuple(int(x) for x in secstab.__version__.split('.')[:2]) < (0,2):
        raise ValueError('Run git pull first: this package needs secstab source version >=0.2')
    checks = json.loads((bundle/'checksums.json').read_text(encoding='utf-8'))
    for relative,expected in checks.items():
        source = confined(bundle,relative)
        if not source.is_file() or digest(source) != expected:
            raise ValueError('Package hash mismatch: '+relative)
    manifest = bundle/'data/corpus_extracted_v1.json'
    records = json.loads(manifest.read_text(encoding='utf-8'))
    if len(records) != 12 or len({r['document_id'] for r in records}) != 12:
        raise ValueError('Expected the 12-document pilot')
    for r in records:
        for kind in ('raw','submissions'):
            source = confined(project,r[kind+'_path'])
            if digest(source) != r[kind+'_sha256']:
                raise ValueError('Your original filing/metadata differs: '+r['ticker']+' '+kind)
        for kind in ('text','source_map'):
            source = confined(bundle,r[kind+'_path'])
            if digest(source) != r[kind+'_sha256']:
                raise ValueError('Corpus payload differs: '+r['ticker']+' '+kind)
        if r['review_status'] != 'ai_assisted_passed' or r['review_scope'] != 'descriptive_pilot_only':
            raise ValueError('Unexpected review state')
    # Check EVERY destination before copying anything. Existing matching files are idempotent.
    payload = {k:v for k,v in checks.items() if k.startswith('data/')}
    for relative,expected in payload.items():
        target=confined(project,relative)
        if target.exists() and (not target.is_file() or digest(target)!=expected):
            raise ValueError('Refusing to replace existing file: '+relative)
    created=0
    for relative in payload:
        target=confined(project,relative)
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as out, confined(bundle,relative).open('rb') as source:
                shutil.copyfileobj(source,out)
            created+=1
    from secstab.cli import corpus
    with chdir(project):
        corpus(Path('data/corpus_extracted_v1.json'))
    print(f'Installed and validated 12 source-matched Risk Factors sections ({created} new files).')
    print('Existing data/corpus.json and manual text files were not changed.')
    print('Ready corpus: data/corpus_extracted_v1.json')
    print('Review scope: AI-assisted source/boundary checks for descriptive pilot only; no independent human audit.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',default='.')
    args=p.parse_args()
    install(Path(__file__).resolve().parent,Path(args.project))


if __name__=='__main__':
    main()
