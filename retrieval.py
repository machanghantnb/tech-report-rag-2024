import collections,json,os,pathlib,pickle,re,time
import jieba,numpy as np
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi
ROOT=pathlib.Path(__file__).resolve().parent; DATA=ROOT/'data'
MODEL='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
os.environ.setdefault('HF_HUB_DISABLE_XET','1')
jieba.setLogLevel(40)
jieba.dt.tmp_dir=str(DATA)

def tokens(text):
    return [w.lower() for w in jieba.lcut(text) if re.search(r'[\w\u4e00-\u9fff]',w)]

def embedding_model():
    if list((DATA/'models').glob('models--*/snapshots/*/config.json')):
        os.environ['HF_HUB_OFFLINE']='1'
    return TextEmbedding(MODEL,cache_dir=str(DATA/'models'),threads=4)

class Engine:
    def __init__(self):
        self.chunks=[json.loads(l) for l in (DATA/'chunks.jsonl').read_text(encoding='utf-8').splitlines()]
        self.sources=json.loads((DATA/'sources.json').read_text(encoding='utf-8'))
        self.bycode={s['code']:s for s in self.sources}
        self.vectors=np.load(DATA/'index/vectors.npy',mmap_mode='r')
        with (DATA/'index/bm25.pkl').open('rb') as f: self.bm25=pickle.load(f)
        self.model=embedding_model()
        self.company_idx={s['code']:np.array([i for i,c in enumerate(self.chunks) if c['code']==s['code']]) for s in self.sources}

    def search(self,question,mode='hybrid',panorama=False,k=10):
        if mode not in ['hybrid','bm25','vector']: raise ValueError('未知检索方式')
        query=question
        # Remove company names from content scoring; metadata supplies company filters.
        selected=[s['code'] for s in self.sources if s['company'] in question or s['code'] in question]
        for s in self.sources: query=query.replace(s['company'],'').replace(s['code'],'')
        bm=self.bm25.get_scores(tokens(query))
        vec=np.zeros(len(self.chunks))
        if mode!='bm25':
            q=np.array(next(iter(self.model.query_embed(query))),dtype=np.float32); q/=max(np.linalg.norm(q),1e-12)
            vec=self.vectors@q
        def ranked(indices,limit):
            b=indices[np.argsort(-bm[indices],kind='stable')[:80]]
            v=indices[np.argsort(-vec[indices],kind='stable')[:80]]
            scores=collections.defaultdict(float)
            lists=[b] if mode=='bm25' else [v] if mode=='vector' else [b,v]
            for ranking in lists:
                for rank,i in enumerate(ranking,1): scores[int(i)]+=1/(60+rank)
            ordered=sorted(scores,key=lambda i:(-scores[i],i))
            # A page may contain multiple blocks; keep up to 2 to avoid repeated evidence.
            result=[]; seen=collections.Counter()
            for i in ordered:
                c=self.chunks[i]; identity=(c['code'],c['page'])
                if seen[identity]>=2: continue
                result.append((i,scores[i]));seen[identity]+=1
                if len(result)>=limit:break
            return result
        broad=panorama or bool(re.search(r'12家|十二家|所有公司|全部公司|各公司',question))
        if broad or len(selected)>1:
            codes=selected or list(self.company_idx)
            results=[]
            for code in codes: results.extend(ranked(self.company_idx[code],3 if len(codes)>4 else 5))
        else:
            indices=self.company_idx[selected[0]] if selected else np.arange(len(self.chunks))
            results=ranked(indices,k)
        out=[]
        for i,score in results:
            c=dict(self.chunks[i]);c.update(rrf_score=round(score,6),bm25_score=round(float(bm[i]),4),vector_score=round(float(vec[i]),4),file=self.bycode[c['code']]['file']);out.append(c)
        return out

def build():
    folder=DATA/'index';folder.mkdir(exist_ok=True)
    chunks=[json.loads(l) for l in (DATA/'chunks.jsonl').read_text(encoding='utf-8').splitlines()]
    print('Building BM25',flush=True)
    bm=BM25Okapi([tokens(c['text']) for c in chunks])
    with (folder/'bm25.pkl').open('wb') as f:pickle.dump(bm,f)
    model=embedding_model(); batches=[];start=time.time()
    # Checkpoint batches, so interrupted computation does not discard finished work.
    for offset in range(0,len(chunks),256):
        checkpoint=folder/f'batch_{offset:06d}.npy'
        if checkpoint.exists(): v=np.load(checkpoint)
        else:
            v=np.array(list(model.embed([c['text'] for c in chunks[offset:offset+256]],batch_size=32)),dtype=np.float32)
            v/=np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-12)
            np.save(checkpoint,v)
        batches.append(v)
        print(f'{min(offset+256,len(chunks))}/{len(chunks)} ({time.time()-start:.0f}s)',flush=True)
    np.save(folder/'vectors.npy',np.concatenate(batches))
    (folder/'meta.json').write_text(json.dumps(dict(model=MODEL,dim=384,chunks=len(chunks),bm25={'k1':1.5,'b':0.75},fusion='RRF, k=60; top80 per retriever',chunk_chars=320,overlap_chars=50),ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':build()
