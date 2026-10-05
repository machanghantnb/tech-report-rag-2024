"""全文抽取；PDF物理页码从1开始；表格以行列保存并随块携带表头。"""
import concurrent.futures,json,pathlib,re
import pymupdf
ROOT=pathlib.Path(__file__).resolve().parent
DATA=ROOT/'data'

def split_text(text,limit=320,overlap=50):
    text=text.strip()
    while len(text)>limit:
        end=max(text.rfind('。',limit//2,limit),text.rfind('\n',limit//2,limit))
        end=end+1 if end>0 else limit
        yield text[:end]
        text=text[max(1,end-overlap):]
    if text.strip(): yield text

def extract_one(s):
    doc=pymupdf.open(DATA/'reports'/s['file']); pages=[]; chunks=[]; tables=[]
    section='封面及重要提示'
    for n,p in enumerate(doc,1):
        text=p.get_text('text',sort=True)
        # Ignore repeated running headers and printed page numbers when chunking.
        lines=text.splitlines()
        body='\n'.join(l for l in lines if not re.match(r'^\s*\d+\s*/\s*\d+\s*$',l) and not ('2024' in l and '年度报告' in l and len(l)<70))
        headings=re.findall(r'^\s*第[一二三四五六七八九十百\d]+[章节]\s*[^\n]{2,35}',body,re.M)
        if headings and not ('目录' in body[:200] or '目 录' in body[:200]): section=headings[0].strip()
        meta={k:s[k] for k in ['code','company','year','title','url']}
        meta.update(page=n,section=section)
        pages.append(dict(meta,text=text))
        found=p.find_tables(strategy='lines_strict').tables
        table_rects=[]
        for ti,t in enumerate(found):
            rows=[[re.sub(r'\s+',' ',v or '').strip() for v in row] for row in t.extract()]
            if len(rows)<2 or max(map(len,rows),default=0)<2: continue
            table_rects.append(pymupdf.Rect(t.bbox))
            tid=f"{s['code']}-p{n:03d}-t{ti+1}"
            tables.append(dict(meta,id=tid,rows=rows,bbox=list(t.bbox)))
            # Keep unit labels just above the table, instead of silently losing 元/千元.
            above=p.get_text('text',clip=pymupdf.Rect(0,max(0,t.bbox[1]-65),p.rect.width,t.bbox[1]),sort=True)
            units=' '.join(l.strip() for l in above.splitlines() if '单位' in l or '币种' in l)
            header_count=1 if any(re.search(r'20\d{2}|本期|项目|主要会计数据|主要财务指标',v) for v in rows[0]) else min(2,len(rows))
            header=(units+'\n' if units else '')+'\n'.join(' | '.join(row) for row in rows[:header_count])
            for ri in range(header_count,len(rows),3):
                content=header+'\n'+'\n'.join(' | '.join(row) for row in rows[ri:ri+3])
                chunks.append(dict(meta,id=f'{tid}-r{ri+1}',kind='table',text=content,table_id=tid,row_start=ri+1,row_end=min(ri+3,len(rows))))
            if len(rows)==header_count: chunks.append(dict(meta,id=tid+'-r1',kind='table',text=header,table_id=tid,row_start=1,row_end=header_count))
        # Keep layout text too: tables with no drawn borders may not be detected.
        for i,part in enumerate(split_text(body)):
            chunks.append(dict(meta,id=f"{s['code']}-p{n:03d}-b{i+1:02d}",kind='text',text=part))
    print(s['company'],len(pages),'pages',len(tables),'tables',len(chunks),'chunks',flush=True)
    return pages,tables,chunks

if __name__=='__main__':
    sources=json.loads((DATA/'sources.json').read_text(encoding='utf-8'))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as ex: results=list(ex.map(extract_one,sources))
    for idx,name in enumerate(['pages','tables','chunks']):
        with (DATA/f'{name}.jsonl').open('w',encoding='utf-8') as f:
            for result in results:
                for item in result[idx]: f.write(json.dumps(item,ensure_ascii=False)+'\n')
    stats={name:sum(len(r[i]) for r in results) for i,name in enumerate(['pages','tables','chunks'])}
    stats['companies']=len(sources)
    (DATA/'stats.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    print(stats)
