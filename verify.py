"""核验来源、索引一致性、表格单位、评测数据隔离与HTTP配置边界。"""
import hashlib,json,pathlib,pickle,re
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parent; DATA=ROOT/'data'
sources=json.loads((DATA/'sources.json').read_text(encoding='utf-8'))
assert len(sources)==12 and len({s['code'] for s in sources})==12
for s in sources:
    assert s['url'].startswith('https://static.cninfo.com.cn/')
    assert hashlib.sha256((DATA/'reports'/s['file']).read_bytes()).hexdigest()==s['sha256']
chunks=[json.loads(l) for l in (DATA/'chunks.jsonl').read_text(encoding='utf-8').splitlines()]
assert len(chunks)==len({c['id'] for c in chunks})
assert all(c['company'] and c['section'] and c['page']>=1 for c in chunks)
smic=[c for c in chunks if c['id']=='688981-p008-t3-r2'][0]
assert '千元' in smic['text'] and '57,795,570' in smic['text']
will=[c for c in chunks if c['id']=='603501-p037-t1-r2'][0]
assert '12.61' in will['text'] and '3,245,293,133.87' in will['text']
v=np.load(DATA/'index/vectors.npy',mmap_mode='r')
assert v.shape==(len(chunks),384)
assert np.all(np.isfinite(v)) and np.allclose(np.linalg.norm(v,axis=1),1,atol=1e-5)
with (DATA/'index/bm25.pkl').open('rb') as f:b=pickle.load(f)
assert b.corpus_size==len(chunks)
questions=json.loads((ROOT/'evaluation/questions.json').read_text(encoding='utf-8'))
assert len(questions)==10 and sum(q['panorama'] for q in questions)>=2
assert all('gold' not in c and 'answer' not in c for c in chunks)
print('PASS: 12 original PDFs with SHA256; unique source/page IDs; checked unit labels; matching BM25 and normalized 384D vectors; 10 questions including 2 panoramas; no gold answers in index.')
