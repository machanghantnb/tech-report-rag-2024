"""依据已核对的真实评测生成一页结论；禁止缺失评测时填造通过率。"""
import json,pathlib
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.pagesizes import A4
ROOT=pathlib.Path(__file__).resolve().parent

def create():
    review=json.loads((ROOT/'evaluation/review.json').read_text(encoding='utf-8'))
    raw=json.loads((ROOT/'evaluation/raw_results.json').read_text(encoding='utf-8'))
    assert len(review['questions'])==10 and len(raw)==10
    assert all(r['generated'] for r in raw), '有题目未生成回答，不能声称已完成10题模型实测'
    font_path=pathlib.Path('C:/Windows/Fonts/simhei.ttf')
    if font_path.exists():pdfmetrics.registerFont(TTFont('CN',str(font_path)))
    else:pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    font='CN' if font_path.exists() else 'STSong-Light'
    body=ParagraphStyle('body',fontName=font,fontSize=9.2,leading=14,textColor=colors.HexColor('#30483e'),spaceAfter=5)
    heading=ParagraphStyle('heading',parent=body,fontSize=11,leading=17,textColor=colors.HexColor('#174f40'),spaceBefore=8,spaceAfter=5)
    title=ParagraphStyle('title',parent=body,fontSize=19,leading=26,spaceAfter=5)
    small=ParagraphStyle('small',parent=body,fontSize=8,leading=11)
    out=ROOT.parent/'方向A_一页结论.pdf'
    doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=37,leftMargin=37,topMargin=31,bottomMargin=28)
    story=[Paragraph('同一批财报，哪些问题适合建库？',title),Paragraph('方向 A | 12家半导体公司2024年年报 | 真实运行与逐题核对',small)]
    story.append(Paragraph('材料与方法',heading))
    story.append(Paragraph('从巨潮资讯下载12份年度报告全文，共2,981页。按公司、章节、PDF页码切块；识别3,567个表格并保留行列及附近单位。<br/>共27,777个文本/表格块。MiniLM 384维语义向量与BM25各取前80名，RRF融合；单公司取10块，全景题每家公司取3块。由DeepSeek基于证据作答。',body))
    model=raw[0].get('model','DeepSeek')
    story.append(Paragraph('实验结果',heading))
    story.append(Paragraph(f"模型：{model}。温度0；10道题，其中2道跨全部12家公司。判定要求：主要事实、单位、年份、比较范围和关键引用均正确。核对由AI助手完成，学生仍可根据原文复核。{review['summary']}",body))
    rows=[[Paragraph(v,small) for v in ['题目','检查内容','结果与原因']]]
    for q in review['questions']:
        rows.append([Paragraph(q['id'],small),Paragraph(q['label'],small),Paragraph(q['verdict']+'：'+q['short_reason'],small)])
    table=Table(rows,colWidths=[37,108,376],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e6efe9')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#abc6b5')),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#dce6df')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.append(table)
    story.append(Paragraph('结论与边界',heading))
    for text in review['conclusions']:story.append(Paragraph(text,body))
    story.append(Paragraph('复现与核验：代码见随附项目；data/sources.json记录下载地址与SHA256；evaluation/raw_results.json记录逐题答案、实际召回块及三种检索结果；evaluation/review.json记录判定。页码统一为PDF物理页码。原始财报及密钥不上传仓库。',small))
    def footer(c,d):
        c.setFont(font,8);c.setFillColor(colors.HexColor('#75877c'));c.drawString(37,18,'人工智能与数据分析 · 作业3 · 方向A');c.drawRightString(A4[0]-37,18,'2026-10-04  /  1')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(out)
if __name__=='__main__':create()

