"""Research CLI. Network/model commands require explicit invocation."""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import numpy as np
from .core import sha256, normalize, shared_chunks, peers, compare


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def now():
    return datetime.now(timezone.utc).isoformat()


def fetch_url(url, ua):
    time.sleep(0.25)  # Sequential requests; no parallel SEC downloads.
    request = Request(url, headers={"User-Agent":ua, "Accept-Encoding":"identity"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def fetch(args):
    ua = os.environ.get("SEC_USER_AGENT", "")
    if "@" not in ua:
        raise ValueError("Set SEC_USER_AGENT to your real name/organization and contact email")
    if Path("data/filings.json").exists():
        raise ValueError("data/filings.json exists; preserve it before starting another collection")
    cfg, records = read(args.universe), []
    for company in cfg["companies"]:
        cik = company["cik"].zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        raw = fetch_url(url, ua)
        sub = json.loads(raw)
        if str(sub["cik"]).zfill(10) != cik:
            raise ValueError("SEC CIK identity mismatch")
        root = Path("data/raw") / cik
        root.mkdir(parents=True, exist_ok=False)
        (root/"submissions.json").write_bytes(raw)
        recent = sub["filings"]["recent"]
        eligible = [i for i, form in enumerate(recent["form"])
                    if form == "10-K" and recent["filingDate"][i] <= cfg["as_of"]]
        if not eligible:
            raise ValueError(f"No recent eligible 10-K for {cik}; manually inspect SEC historical submission files")
        i = max(eligible, key=lambda j: recent["acceptanceDateTime"][j])
        accession, filename = recent["accessionNumber"][i], recent["primaryDocument"][i]
        source_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{filename}"
        source = root / "filing.html"
        source.write_bytes(fetch_url(source_url, ua))
        records.append({**company, "sec_name":sub["name"], "sec_tickers":sub.get("tickers",[]),
            "document_id":accession, "accession":accession, "form":"10-K",
            "filing_date":recent["filingDate"][i], "accepted_at":recent["acceptanceDateTime"][i],
            "report_date":recent["reportDate"][i], "source_url":source_url,
            "raw_path":source.as_posix(), "raw_sha256":sha256(source),
            "submissions_path":(root/"submissions.json").as_posix(),
            "submissions_sha256":sha256(root/"submissions.json"),
            "downloaded_at":now(), "section":"Item 1A Risk Factors",
            "review_status":"pending", "text_path":None, "text_sha256":None,
            "note":"Descriptive as-of-date pilot; availability lag and security mapping not approved for financial backtesting"})
        # Save progress after each successful company. Interrupted collection is retained.
        write("data/filings.json", records)
        print(company["ticker"], accession, source_url)
    print("Download complete. Read docs/DATA_REVIEW.md before admitting text.")


def admit(args):
    filings = read("data/filings.json")
    matches = [r for r in filings if r["document_id"] == args.document_id]
    if len(matches) != 1:
        raise ValueError("Expected exactly one source filing for document_id")
    record = dict(matches[0])
    text_path = Path(args.text)
    if not text_path.is_file() or len(text_path.read_text(encoding="utf-8").strip()) < 100:
        raise ValueError("Expected complete UTF-8 reviewed Item 1A text, not a heading/snippet")
    if sha256(Path(record["raw_path"])) != record["raw_sha256"]:
        raise ValueError("Raw source hash changed")
    record.update(text_path=text_path.as_posix(), text_sha256=sha256(text_path),
                  review_status="passed", reviewer=args.reviewer, review_notes=args.notes, reviewed_at=now())
    corpus = read("data/corpus.json") if Path("data/corpus.json").exists() else []
    if any(r["document_id"] == args.document_id for r in corpus):
        raise ValueError("Already admitted; preserve old corpus and create a new version for revisions")
    corpus.append(record)
    write("data/corpus.json", corpus)
    print("Admitted", args.document_id, "after user-asserted manual source review")


def corpus(path):
    records = read(path)
    ids = [r["document_id"] for r in records]
    if len(set(ids)) != len(ids) or len(records) < 4:
        raise ValueError("Need >=4 unique reviewed documents")
    if len({r["cik"] for r in records}) != len(records):
        raise ValueError("Pilot requires exactly one document per company")
    texts = []
    for r in records:
        status = r.get("review_status")
        ai_review = (status == "ai_assisted_passed" and
                     r.get("review_scope") == "descriptive_pilot_only" and
                     bool(r.get("reviewer")) and bool(r.get("source_map_sha256")))
        if (status != "passed" and not ai_review) or r["section"] != "Item 1A Risk Factors":
            raise ValueError("Only reviewed, same-section documents admitted")
        if ai_review and sha256(Path(r["source_map_path"])) != r["source_map_sha256"]:
            raise ValueError("Changed extraction source map for " + r["document_id"])
        for key in ("raw", "text"):
            if sha256(Path(r[f"{key}_path"])) != r[f"{key}_sha256"]:
                raise ValueError(f"Changed {key} bytes for {r['document_id']}")
        texts.append(Path(r["text_path"]).read_text(encoding="utf-8"))
    return records, ids, texts


def new_run(args):
    records, ids, texts = corpus(args.corpus)
    out = Path("runs") / args.run_id
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
        raise ValueError("run-id must contain letters, numbers, underscores or hyphens")
    out.mkdir(parents=True, exist_ok=False)
    write(out/"corpus_snapshot.json", records)
    versions = {d.metadata["Name"]:d.version for d in importlib.metadata.distributions() if d.metadata["Name"]}
    rev = subprocess.run(["git","rev-parse","HEAD"], capture_output=True, text=True)
    dirty = subprocess.run(["git","status","--porcelain"], capture_output=True, text=True)
    write(out/"manifest.json", {"status":"started", "started_at":now(), "command":sys.argv,
        "git_commit":rev.stdout.strip() or None, "git_status":dirty.stdout,
        "python":sys.version, "packages":versions, "document_order":ids,
        "corpus_sha256":sha256(Path(args.corpus)), "scope":"descriptive pilot; no financial claims"})
    return out, ids, texts


def save_similarity(out, ids, s, k):
    np.save(out/"similarity.npy", s)
    chosen, _, margins = peers(s, k)
    write(out/"peers.json", [{"document_id":d, "peers":[ids[j] for j in chosen[i]],
                            "boundary_margin":float(margins[i])} for i,d in enumerate(ids)])
    manifest = read(out/"manifest.json")
    manifest.update(status="complete", completed_at=now(), outputs={f.name:sha256(f) for f in out.iterdir() if f.is_file() and f.name != "manifest.json"})
    write(out/"manifest.json", manifest)


def tfidf(args):
    from sklearn.feature_extraction.text import TfidfVectorizer
    out, ids, texts = new_run(args)
    vectorizer = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1,2), sublinear_tf=True)
    x = vectorizer.fit_transform(texts)
    write(out/"tfidf.json", {"fit_scope":"entire descriptive pilot corpus; not valid as a historical fit rule", "vocabulary":vectorizer.vocabulary_, "idf":vectorizer.idf_.tolist(), "settings":{"lowercase":True,"stop_words":"english","ngram_range":[1,2],"sublinear_tf":True}})
    save_similarity(out, ids, (x @ x.T).toarray(), args.k)
    print(out)


def lock(args):
    from huggingface_hub import HfApi
    if Path(args.output).exists():
        raise ValueError("Lock file exists; use a different output to preserve model versions")
    cfg = read(args.models)
    for model in cfg["models"]:
        info = HfApi().model_info(model["model_id"], revision="main")
        model["revision"] = info.sha
        model["training_cutoff"] = "unknown; independently review training and fine-tuning documentation"
    cfg["locked_at"] = now()
    cfg["source_config_sha256"] = sha256(Path(args.models))
    write(args.output, cfg)
    print(args.output)


def embed(args):
    from sentence_transformers import SentenceTransformer
    from transformers import AutoTokenizer
    import torch
    cfg = read(args.models)
    models = cfg["models"]
    if any(not re.fullmatch(r"[a-f0-9]{40}", m.get("revision", "")) for m in models):
        raise ValueError("Use lock-models first; immutable revisions required")
    selected = next((m for m in models if m["key"] == args.model), None)
    if selected is None:
        raise ValueError("Unknown model key")
    tokenizers = [(m, AutoTokenizer.from_pretrained(m["model_id"], revision=m["revision"])) for m in models]
    def fits(text):
        return all(len(t(m["prefix"]+text, add_special_tokens=True, truncation=False)["input_ids"]) <= min(args.budget,m["max_length"]) for m,t in tokenizers)
    out, ids, texts = new_run(args)
    torch.manual_seed(0)
    model = SentenceTransformer(selected["model_id"], revision=selected["revision"], device=args.device)
    model.eval()
    model.max_seq_length = min(args.budget,selected["max_length"])
    # Supply already-prefixed inputs; suppress any checkpoint default prompt.
    model.default_prompt_name = None
    vectors, chunk_rows = [], []
    for doc_id, text in zip(ids,texts):
        spans = shared_chunks(text, fits)
        chunks = [text[a:b] for a,b in spans]
        inputs = [selected["prefix"]+chunk for chunk in chunks]
        actual = model.tokenizer(inputs, add_special_tokens=True, truncation=False)["input_ids"]
        if any(len(tokens) > model.max_seq_length for tokens in actual):
            raise ValueError("Input would truncate; model/tokenizer contract mismatch")
        e = model.encode(inputs, batch_size=args.batch_size, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True, prompt="")
        # Equal weighting keeps cross-model aggregation weights identical.
        vectors.append(normalize(np.mean(e,axis=0)))
        for a,b in spans:
            chunk_rows.append({"document_id":doc_id, "start_char":a, "end_char":b,
                               "span_sha256":hashlib.sha256(text[a:b].encode()).hexdigest()})
    z = np.vstack(vectors)
    np.save(out/"embeddings.npy", z)
    write(out/"chunks.json", chunk_rows)
    write(out/"models_snapshot.json",cfg)
    write(out/"embedding_settings.json", {"model":selected,"total_token_budget":args.budget,"aggregation":"equal mean of normalized chunk vectors, then L2 normalize","device":args.device,"dtype":str(next(model.parameters()).dtype),"pooling_modules":str(model),"torch_version":torch.__version__,"cuda_version":torch.version.cuda,"cuda_device":torch.cuda.get_device_name() if args.device.startswith("cuda") else None,"repeatability":"One fixed-weight inference; no independent training-seed experiment"})
    save_similarity(out, ids, z @ z.T, args.k)
    print(out)


def compare_runs(args):
    a,b = Path(args.a),Path(args.b)
    ma,mb = read(a/"manifest.json"),read(b/"manifest.json")
    if ma["status"] != "complete" or mb["status"] != "complete":
        raise ValueError("Both runs must be complete")
    if ma["corpus_sha256"] != mb["corpus_sha256"] or ma["document_order"] != mb["document_order"]:
        raise ValueError("Runs must use the identical corpus and order")
    for root, manifest in ((a,ma),(b,mb)):
        for name, digest in manifest["outputs"].items():
            if sha256(root/name) != digest:
                raise ValueError("Run output hash changed: " + str(root/name))
    if Path(args.output).exists():
        raise ValueError("Comparison exists; choose another output")
    result = compare(np.load(a/"similarity.npy"),np.load(b/"similarity.npy"),ma["document_order"],args.k)
    result.update(run_a=str(a),run_b=str(b),manifest_a_sha256=sha256(a/"manifest.json"),manifest_b_sha256=sha256(b/"manifest.json"),created_at=now())
    write(args.output,result)
    print(json.dumps({key:value for key,value in result.items() if key != "companies"},indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command",required=True)
    p = sub.add_parser("fetch"); p.add_argument("--universe",default="configs/universe.json"); p.set_defaults(func=fetch)
    p = sub.add_parser("admit"); p.add_argument("--document-id",required=True); p.add_argument("--text",required=True); p.add_argument("--reviewer",required=True); p.add_argument("--notes",required=True); p.set_defaults(func=admit)
    p = sub.add_parser("lock-models"); p.add_argument("--models",default="configs/models.json"); p.add_argument("--output",default="configs/models.lock.json"); p.set_defaults(func=lock)
    for command,func in (("tfidf",tfidf),("embed",embed)):
        p = sub.add_parser(command); p.add_argument("--corpus",default="data/corpus.json"); p.add_argument("--run-id",required=True); p.add_argument("--k",type=int,default=2); p.set_defaults(func=func)
        if command == "embed":
            p.add_argument("--models",default="configs/models.lock.json"); p.add_argument("--model",required=True); p.add_argument("--budget",type=int,default=192); p.add_argument("--device",default="cpu"); p.add_argument("--batch-size",type=int,default=8)
    p = sub.add_parser("compare"); p.add_argument("--a",required=True); p.add_argument("--b",required=True); p.add_argument("--output",required=True); p.add_argument("--k",type=int,default=2); p.set_defaults(func=compare_runs)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
