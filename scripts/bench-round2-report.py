"""第二轮报告：保留不完整状态，不给混合任务总准确率"""
import datetime,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'data/outputs/bench-20261030b';REPORT=ROOT/'data/reports'
new=json.loads((REPORT/'benchmark-round2.json').read_text());old=json.loads((REPORT/'benchmark-20261030.json').read_text());names={'vision':'Apple Vision','glm':'GLM-OCR / MLX','paddlevl':'PaddleOCR-VL-1.6 / MLX','mineru':'MinerU 4.1.2 Basic','tesseract':'Tesseract补测'}
lines=['# OCR第二轮实测 · 2026-10-30','','## 范围与口径','','沿用40份中文及混排、20份英文的balanced60-v1，另6份开发预检；输入PNG与第一轮一致。新增原生Apple路线、两款MLX视觉模型、MinerU Basic，并补Tesseract子进程内存。详情见[协议](../../docs/benchmark-round2.md)','','GLM/PaddleOCR-VL是固定提示词的整图模型调用，没有接官方布局切分流水线；MinerU是Basic完整小模型流水线，不代表其Standard/Advanced表现。没有新增全页人工答案集，以下覆盖率不是整体正确率，也没有把1减覆盖率称为错字率','','## 正式60份结果','','表单/文档为严格片段字符覆盖宏平均；街景为答案检出率；招牌为CER（34参考字符、越低越好）。不同行可能使用CPU、Metal GPU或系统自动调度，速度不是同设备算力对照','','| 方案 | 正常返回/60 | 中文表单↑ | 英文表单↑ | 混合文档↑ | 街景答案↑ | 招牌CER↓ | 60份处理秒 | 采样RSS峰值GiB |','| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
for e,r in new.items():
 q=r['quality'];t=r['timing'];lines.append(f"| {names[e]} | {t['success']} | {q['XFUND']['macro_mean']:.1%} | {q['FUNSD']['macro_mean']:.1%} | {q['OmniDocBench']['macro_mean']:.1%} | {q['ESTVQA']['macro_mean']:.1%} | {q['ReCTS']['micro_cer']:.1%} | {t['inference_seconds']:.2f} | {r['resources']['peak_tree_rss_bytes']/1024**3:.2f} |")
lines+=['','正常返回只指未报错且未触发长度截断，不代表内容正确或非空。Vision有1份空输出（omni-019）；Tesseract有10份空输出，均保留评分。GLM截断率5%，PaddleOCR-VL截断率10%，这是运行完整性指标，不是错字率','','RSS是每200ms父进程及后代之和：可能漏瞬时尖峰、重复计算共享页，且不含进程树外的Apple系统服务。不能当作全系统物理内存，不能和MLX内存池相加。第一轮ru_maxrss与本轮采样方法也不同','','## 单页时间与MLX内存池','','| 方案 | 中位秒 | P95秒 | MLX池峰值GiB |','| --- | --- | --- | --- |']
for e,r in new.items():
 vals=[]
 for row in json.loads((ROOT/'data/manifests/balanced60.json').read_text())['cases']:
  d=json.loads((BASE/e/'full'/(row['case_id']+'.json')).read_text())
  if 'mlx_peak_bytes' in d:vals.append(d['mlx_peak_bytes'])
 mx=f'{max(vals)/1024**3:.2f}' if vals else '不适用'
 lines.append(f"| {names[e]} | {r['timing']['median']:.2f} | {r['timing']['p95']:.2f} | {mx} |")
lines+=['','## 初始化、预热和运行失败','','初始化不含预热中的延迟加载；Vision未单独计初始化。均在已安装、模型已下载后测量','','| 方案 | 初始化秒 | 预热秒 | 整轮进程墙钟秒 | 失败/截断 |','| --- | --- | --- | --- | --- |']
for e,r in new.items():
 warm=json.loads((BASE/e/'full/warmup.json').read_text())
 init=r['setup'].get('init_seconds');init=f'{init:.2f}' if init is not None else '未单独计'
 lines.append(f"| {names[e]} | {init} | {warm['seconds']:.2f} | {r['resources']['wall_seconds']:.2f} | {60-r['timing']['success']}/60 |")
lines+=['','失败清单：','']
for e in new:
 failed=[x for x in json.loads((BASE/e/'full/summary.json').read_text())['results'] if x['status']!='ok']
 if failed:lines.append('- '+names[e]+'：'+', '.join(x['case_id']+' ('+x['status']+')' for x in failed))
lines+=['','## 旧扫描的局部严格断言','','这些是自定义严格检查，不是olmOCR官方分数；参考只覆盖部分文字，不代表整页正确率','','| 方案 | 应出现文本 /17 | 顺序 /11 | 不应出现 /8 |','| --- | --- | --- | --- |']
for e,r in new.items():
 q=r['quality']['olmOCR-bench']['by_type'];lines.append('| '+names[e]+' | '+' | '.join(str(q[t]['passed']) for t in ['present','order','absent'])+' |')
lines+=['','## 本轮判断','','- MinerU Basic值得保留作为中文文档候选：中文表单86.8%，高于第一轮PaddleOCR的76.4%；60份约123秒，未报错/截断。不过街景和小招牌较弱，不能替代所有场景','- Apple Vision适合作为Mac快速识字候选：约33秒，中文表单73.6%，街景答案6/6命中；英文表单与旧扫描表现较弱，真实GUI截图仍需另测','- GLM整图模式在英文表单（67.6%）、混合文档（47.4%）和小招牌（CER5.9%）有增益，但约793秒且3份截断，适合有失败检测的专项尝试','- PaddleOCR-VL当前整图配置不优先作为默认方案：54/60未截断，6份触及上限；这不代表官方布局切分流水线的效果','- 继续保留第一轮RapidOCR/PaddleOCR日常路线。下一步优先人工校对答案、真实GUI和表格结构测试，再考虑VLM官方切块流水线；不靠不断增加模型数量代替评价质量','','招牌仅6张、34参考字符：GLM错2字符、5/6整行完全匹配；这不足以说明所有中文场景有94.1%准确率。各项覆盖率也不能直接换算为错字率','']
lines+=['','## 执行状态与边界','']
for e in ['vision','glm','paddlevl','mineru','tesseract']:
 if e in new:lines.append(f'- {names[e]}：完成60份，成功{new[e]["timing"]["success"]}份；失败/截断保留在分母内')
 else:
  f=BASE/e/'preflight/exit.json';d=json.loads(f.read_text()) if f.exists() else {};lines.append(f'- {names[e]}：未形成完整60份结果；预检退出信息 {json.dumps(d,ensure_ascii=False)}')
lines+=['','GLM首次正式轮在整机变慢时被保守停止，事后已完成页MLX峰值仅约3.1–3.2GiB，不能归因于模型引发内存压力。加入16GiB分配上限、1GiB缓存上限后重新完整测量，旧轮不混入最终成绩。单页生成上限8192 tokens，达到上限记truncated；有输出不等于完整成功','','MinerU首次预检因测试脚本缺少多进程main入口保护而失败；修正后重新预检，旧日志保留。其Markdown内嵌图片data URI在评分前剥离，原始输出保留，避免把图片编码误当成文字。此修复不属于模型识别失败','','安装发生PyPI文件下载超时，MLX关键wheel改用镜像下载并对照PyPI官方SHA256；MinerU使用镜像安装。环境隔离在.venv-mlx和.venv-mineru，不修改原有OCR全局工具，也未启动常驻API服务','','## 抽查发现','','GLM-OCR整图模式在omni-024密集报纸页出现重复段落，并在xfund-zh_val_28、xfund-zh_val_8两份表单触发8192 token上限，共3份记录为truncated；其中一份表单末尾反复输出“空”。输出很长不等于识别完整；未用额外token无限放宽预算来掩盖失败。尚未对该页尝试官方布局切块流水线，不能据此断言完整GLM-OCR产品也一定失败','','PaddleOCR-VL整图模式共6份触及长度上限；抽查发现报纸重复人名、表单重复下划线、街景重复“福”等。失败清单和原始输出已保留，不把补写或循环生成当作真实文字','','## 磁盘与复现','','两款VLM权重约3.85GiB，MinerU Basic模型约0.80GiB；环境目录逻辑大小约0.76和1.2GiB。目录合计约6.6GiB，仅作当前文件规模说明，缓存/硬链接复用使其不等于物理新增量；不重复保留原版+转换版模型','','- [逐样本指标](benchmark-round2.csv)、[配置/内存/质量JSON](benchmark-round2.json)','- [第一轮报告](benchmark-20261030.md)、[MLX依赖冻结](requirements-mlx.txt)、[MinerU依赖冻结](requirements-mineru.txt)','- 本地原始证据：data/outputs/bench-20261030b；模型提交号与下载记录位于setup/vlm-models.json；不将大批原始文字和模型提交Git','- [模型提交与校验记录](benchmark-round2-models.json)、[安装残片清理记录](round2-download-cleanup.json)',
'- [运行器](../../scripts/bench-round2-run.py)、[评分器](../../scripts/bench-round2-score.py)、[Apple源代码](../../scripts/bench-vision.swift)','']
start=datetime.datetime.fromisoformat(json.loads((ROOT/'configs/benchmark-round2.json').read_text())['started_utc']);end=datetime.datetime.now(datetime.timezone.utc)
lines+=['## 时间范围','',f'从配置记录起点{start.astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime("%H:%M:%S")}至报告生成{end.astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime("%H:%M:%S")}，墙钟跨度约{(end-start).total_seconds()/60:.1f}分钟，包含对话中断、网络等待、环境安装、诊断和测试。各引擎纯处理时间已单列，不能将整个跨度算成推理耗时','']
(REPORT/'benchmark-round2.md').write_text('\n'.join(lines));print('report engines',list(new))
