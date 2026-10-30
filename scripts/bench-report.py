"""由实测JSON生成可纳入Git的汇总，原文留在本地输出"""
import csv
import datetime
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1];base=root/'data/outputs/bench-20261030';reports=root/'data/reports'
scores=json.loads((base/'scores.json').read_text());compact={};rows=[]
for engine,s in scores.items():
 compact[engine]={k:v for k,v in s.items() if k!='cases'}
 for r in s['cases']:
  rows.append({k:r[k] for k in ['case_id','dataset','stratum','language_group','status','seconds','metric','value']}|{'engine':engine})
(reports/'benchmark-20261030.json').write_text(json.dumps(compact,ensure_ascii=False,indent=2)+'\n')
with (reports/'benchmark-20261030.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['engine','case_id','dataset','stratum','language_group','status','seconds','metric','value']);w.writeheader();w.writerows(rows)
names={'rapid':'RapidOCR 3.8.1 / PP-OCRv4 ONNX','paddle':'PaddleOCR 3.5.0 / PP-OCRv5 mobile','tesseract':'Tesseract 5.5.2','easy':'EasyOCR 1.7.2','docling':'Docling / RapidOCR + Heron + TableFormer'}
lines=['# OCR 轻量实测报告 · 2026-10-30','','## 范围与结论','','使用新冻结的60份输入：中文及混排40份、英文20份。每个进入正式测试的引擎使用同一份RGB图像，CPU4线程，长边上限2000像素，PDF统一光栅化。额外6份开发样本用于预检，不计入60份质量结果','','本轮是本机、固定配置、小样本的工程筛选；评分没有逐字人工金标准，不给总准确率或通用排行榜。具体配置、准入和计分见[测试协议](../../docs/benchmark-protocol.md)，源数据见[物料名单](balanced60-materials.md)','','测试领域：24份中英文表单、18份混合文档（教材/报告各3，PPT/论文/书页/试卷/笔记各2，历史文档/报纸各1）、6份旧扫描、6份街景问答图、6份裁剪招牌行。裁剪行合计仅34个参考字符，结果不宜外推为稳定总体比例','','## 完成情况与速度','','下表推理时间是60份单样本耗时之和，不含初始化和预热；中位数/P95为单样本秒数。CLI逐页启动开销包含在Tesseract时间内','','| 方案 | 成功 | 60份推理 | 中位数 | P95 | 初始化 | 预热 |','| --- | --- | --- | --- | --- | --- | --- |']
for e,s in scores.items():
 t=s['timing'];sm=s['summary'];lines.append(f"| {names[e]} | {t['success']}/60 | {t['inference_seconds']:.2f}s | {t['median']:.2f}s | {t['p95']:.2f}s | {sm['init_seconds']:.2f}s | {sm['warmup_seconds']:.2f}s |")
lines+=['','单次测量，非重复压测；新增依赖安装/模型下载与部分测试重叠，机器未做专用性能隔离。首次下载及冷启动单独见准备记录，不应加到热推理中作同口径比较','','## 分领域质量','','覆盖率是“整个参考文本块/实体/单元格完全命中”的字符加权覆盖，再按页宏平均，**不是逐字符识别准确率**。ReCTS CER越低越好；其他列越高越好','','| 方案 | 中文表单 XFUND14 | 英文表单 FUNSD10 | 混合文档 Omni18 | 街景答案6 | 招牌行 CER / 完全匹配 |','| --- | --- | --- | --- | --- | --- |']
for e,s in scores.items():
 q=s['quality'];pct=lambda k:f"{q[k]['macro_mean']:.1%}"
 lines.append(f"| {e} | {pct('XFUND')} | {pct('FUNSD')} | {pct('OmniDocBench')} | {round(q['ESTVQA']['macro_mean']*6)}/6 | {q['ReCTS']['micro_cer']:.1%} / {q['ReCTS']['exact_count']}/6 |")
lines+=['','旧扫描6页只带部分断言，单独列出自定义严格检查；不能理解为整页文字准确率，也不是olmOCR官方分数','','| 方案 | 应出现文本 /17 | 先后顺序 /11 | 不应出现文本 /8 |','| --- | --- | --- | --- |']
for e,s in scores.items():
 q=s['quality']['olmOCR-bench']['by_type'];lines.append('| '+e+' | '+' | '.join(str(q[t]['pass']) for t in ['present','order','absent'])+' |')
lines+=['','## 人工抽查与解释','','- 视觉复核了ReCTS六份裁剪招牌：存在艺术字体、压缩、低对比和较小字高；RapidOCR在“甜客汉堡”等图片出现检测/识别失效，不是单纯普通中文字体测试。默认整页检测流程未针对单行图优化','- XFUND的zh_val_28顶部参考是“中山半xPINGAN”，实际可见“中国平安 PING AN”；说明上游参考本身有误。此次保持冻结参考不事后改分，结果只用于初筛','- 同一表单中Tesseract同时加载简繁英语言包，部分简体内容输出为繁体，严格评分会失分。当前分数代表固定多语言配置，不能推断它在英文专用或指定单行模式下的上限','- 文档中长段落、数学表达和跨列阅读顺序会使严格整块命中下降；不把覆盖率直接称为OCR准确率','- 表格结构、公式、字段关联没有经过人工金标准评分；即使输出Markdown/JSON，也不认定结构正确','- 这60份缺实际桌面/游戏GUI截图，也没有系统覆盖多书写者手写，不推广到所有截图和手写场景','','## 未测方案与执行决定','','- GLM-OCR官方原版权重约2.47 GiB、PaddleOCR-VL-1.6约1.79 GiB，超过本轮单方案新增权重1 GiB软预算，未运行，也未改用量化版或云API','- MinerU4.x本轮暂缓：并非64 GiB机器跑不动，而是限制新增运行时和安装范围，先用Docling覆盖文档流水线。Basic小模型路线仍值得下一轮单独测','- 预检不通过、超时或环境未就绪的方案必须在最终结论补充实际状态，不与完成60份者混排','','官方来源：[GLM-OCR](https://huggingface.co/zai-org/GLM-OCR)、[PaddleOCR-VL](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6)、[MinerU](https://github.com/opendatalab/MinerU)。权重字节数与提交号见本地setup/vlm-precheck.json','','## 复跑与证据','','- [逐样本指标CSV](benchmark-20261030.csv)、[版本/配置/耗时汇总JSON](benchmark-20261030.json)','- 本地原始输出：data/outputs/bench-20261030/{engine}/{preflight,full}/，每份JSON含文字、状态、时间、输入哈希；不把大批输出加入Git','- [运行脚本](../../scripts/bench-run.py)、[评分脚本](../../scripts/bench-score.py)、[配置](../../configs/benchmark.json)、uv.lock固定新增Python环境','- 全局复用RapidOCR/PaddleOCR用户级uv工具和Homebrew Tesseract；EasyOCR/Docling位于项目.venv。模型缓存独立于项目，可复用，不需要全部全局安装CLI','- 当前目录尚未初始化Git；本报告、脚本、配置及清单为Git就绪文件，未提交；CI未配置，完整模型测试本机执行','']
(reports/'benchmark-20261030.md').write_text('\n'.join(lines))
print('report',list(scores))
# 追加诊断不替换主测：根据主测暴露的问题进行任务模式适配
path=base/'cropped-diagnostic.json'
if path.exists():
 diag=json.loads(path.read_text());text=['','## 裁剪文字行追加诊断','','此项在看到主测结果后追加，不是独立留出验证，也不与主测混分。输入仍是同6份ReCTS；RapidOCR关闭检测/方向分类直接识别，Tesseract改psm7及chi_sim+eng','','| 配置 | 字符错误率 | 完全匹配 | 合计耗时 |','| --- | --- | --- | --- |']
 for engine in dict.fromkeys(r['engine'] for r in diag):
  rs=[r for r in diag if r['engine']==engine];err=sum(r['errors'] for r in rs)/sum(r['reference_chars'] for r in rs)
  text.append(f"| {engine} | {err:.1%} | {sum(r['errors']==0 for r in rs)}/6 | {sum(r['seconds'] for r in rs):.2f}s |")
 text+=['','RapidOCR的CER由主测58.8%降至8.8%，说明单行输入应区分检测+识别与仅识别。该差异不能归因为换了模型，也不能据此宣称所有中文场景都达到此水平','']
 with (reports/'benchmark-20261030.md').open('a') as f:f.write('\n'.join(text))
# 计时范围和资源证据
start=datetime.datetime.fromisoformat(json.loads((root/'configs/benchmark.json').read_text())['started_utc'].replace('Z','+00:00'))
now=datetime.datetime.now(datetime.timezone.utc)
meta={'started_utc':start.isoformat(),'report_generated_utc':now.isoformat(),'elapsed_minutes':(now-start).total_seconds()/60,'full_engine_count':len(scores),'main_cases':60,'main_inferences':60*len(scores),'preflight_cases_per_engine':6,'device':'Apple M4 Max, 64 GiB, macOS26.3','uv_install_note':'Resolved22.99s + Prepared13m49s + Installed0.65s; about14min13s','docling_models_download_seconds':120.10562491416931}
(reports/'benchmark-run.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
with (reports/'benchmark-20261030.md').open('a') as f:
 f.write('\n## 准备时间、资源和操作记录\n\n')
 f.write(f"计时起点为配置落盘的北京时间13:30:08，报告生成时累计约{meta['elapsed_minutes']:.1f}分钟，包括下载、接入、诊断、串行测试与报告整理；不等于纯推理用时，也不包含更早的物料调研\n\n")
 f.write('本机Apple M4 Max、64 GiB、macOS26.3。统一输入准备约22秒；新增Python依赖解析与下载安装约14分13秒（项目.venv约1.3 GiB，复用uv缓存）；Docling模型下载约120秒，EasyOCR约100 MiB模型经官方文件内置MD5校验后缓存\n\n')
 f.write('EasyOCR第一次在urllib下载阶段主动中断，改用curl取得相同官方模型；Docling首次正式轮因采集器未保留转换状态而中断，修正后重跑完整60份。中断记录单独保存，不混入最终推理计时和质量分母\n\n')
 f.write('主进程峰值RSS观察：'+ '、'.join(f"{e} {s['summary']['peak_rss_bytes']/1024**3:.2f} GiB" for e,s in scores.items() if e!='tesseract')+'。Tesseract识别在子进程，未将Python父进程RSS作为可比内存数字\n\n')
 f.write('Docling正式轮60份转换状态全部SUCCESS，输出共24个表格对象、覆盖18份输入；这是产物计数，不是表格正确率。抽看omni-001可见产品/公司/收费列已转Markdown，但合并单元格与内容仍需核对\n')
report=reports/'benchmark-20261030.md'
body=report.read_text();intro='''
本轮建议保留 **RapidOCR + Docling** 为日常组合，PaddleOCR作为中文复杂字形/表单的准确性对照。RapidOCR速度最快；Docling增加结构化输出后的总时间仍接近轻量引擎，中文表单覆盖接近PaddleOCR、英文表单覆盖本轮较好

本次固定CPU配置下，EasyOCR耗时约200秒、峰值RSS约17.63 GiB，文本覆盖没有胜出，不优先纳入日常流程；Tesseract保留成熟CLI基线用途，但本轮简繁英组合配置在中文和街景上弱。没有测试各引擎按语言/场景精调后的上限

裁剪文字应区分“检测+识别”和“仅识别”：追加诊断中RapidOCR跳过检测后明显改善。因此“整页提字”和“已裁剪文字行”应该用不同调用方式。复杂旧扫描的严格文本断言通过数普遍偏低，本轮不足以给出可靠识别方案

'''
body=body.replace('## 范围与结论',intro+'## 范围与结论',1)
body=body.replace('- 预检不通过、超时或环境未就绪的方案必须在最终结论补充实际状态，不与完成60份者混排','- 五款入围引擎均通过开发预检和60份正式测试；没有把未运行的三个候选加入质量排名')
body+='''
## 清理与复现状态

已完成新60份正式原图和6份开发图（另含各自参考）的迁移与132文件哈希校验；主测300份输出的状态和输入哈希全部核对通过。当前原件位于data/input/balanced60-v1，开发图位于data/input/development6-v1

旧pilot/zh-expansion采集目录共约176 MiB内容在迁移后删除，另清理重复下载包、旧交接文档与临时筛查副本；仍有用的来源、冻结版本和历史76份清单保留。新结果和本轮诊断证据保留，外部ai-test/sim-dev及welove-job文件未动

[清理明细](material-cleanup.json)、[模型文件校验](benchmark-models.json)、[总计时记录](benchmark-run.json)。`python3 scripts/restore-current.py`可验证或按冻结上游重建当前物料；本轮完成本地全量哈希验证与早期单份恢复验证，尚未在另一台机器全量重建
'''
report.write_text(body)
