"""按已核实的巨潮资讯地址下载12份2024年年报，校验SHA256。"""
import concurrent.futures,hashlib,json,pathlib,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
def download(s):
    folder=ROOT/'data/reports';folder.mkdir(exist_ok=True)
    target=folder/s['file']
    if not target.exists():
        req=urllib.request.Request(s['url'],headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=180) as r: data=r.read()
        if not data.startswith(b'%PDF'):raise ValueError('下载结果不是PDF：'+s['company'])
        target.write_bytes(data)
    if hashlib.sha256(target.read_bytes()).hexdigest()!=s['sha256']:raise ValueError('文件校验不一致：'+s['company'])
    print(s['company'],'已下载并通过校验',flush=True)
if __name__=='__main__':
    sources=json.loads((ROOT/'data/sources.json').read_text(encoding='utf-8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:list(ex.map(download,sources))
