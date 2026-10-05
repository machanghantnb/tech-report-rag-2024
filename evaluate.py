"""保存真实模型输出及召回；正确性由后续逐题核对，不能用关键词命中伪装人工判断。"""
import argparse,datetime,json,pathlib,time
from app import answer,settings
from retrieval import Engine
ROOT=pathlib.Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--retrieval-only',action='store_true');args=parser.parse_args()
    questions=json.loads((ROOT/'evaluation/questions.json').read_text(encoding='utf-8'))
    if not args.retrieval_only and not settings().get('MODEL_API_KEY'):raise SystemExit('请先在本机页面配置DeepSeek密钥。没有模型输出就不能填写回答正确率。')
    import app
    engine=Engine();app.ENGINE=engine
    target=ROOT/'evaluation'/('retrieval_results.json' if args.retrieval_only else 'raw_results.json')
    results=[]
    for q in questions:
        start=time.time(); record=dict(q);record['timestamp']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        record['retrieval_comparison']={}
        for mode in ['bm25','vector','hybrid']:
            evidence=engine.search(q['question'],mode=mode,panorama=q['panorama'])
            hits={code:any(c['code']==code and c['page'] in pages for c in evidence) for code,pages in q['gold_pages'].items()}
            record['retrieval_comparison'][mode]={'ids':[c['id'] for c in evidence],'gold_page_hit_by_company':hits,'note':'页码命中不等于证据完整，更不等于回答正确'}
            if mode=='hybrid': record['evidence']=evidence
        if args.retrieval_only:
            record.update(evidence=engine.search(q['question'],panorama=q['panorama']),answer=None,generated=False)
        else:
            try:record.update(answer(q['question'],panorama=q['panorama']))
            except Exception as e:record.update(error=str(e) if isinstance(e,RuntimeError) else type(e).__name__,answer=None,generated=False)
        record['elapsed_seconds']=round(time.time()-start,2)
        record['correctness']='待核对实际答案' if record.get('generated') else '未调用模型，不能判定回答正确性'
        results.append(record);target.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print(q['id'],'generated=',record['generated'],'seconds=',record['elapsed_seconds'],flush=True)
if __name__=='__main__':main()
