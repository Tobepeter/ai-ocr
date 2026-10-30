# OCR 评价协议 v3

2026-10-30 · v3.1工程修复：独立批次、真实列表标记、失败计时与中断清理 · 本轮固定四方案：RapidOCR、Apple Vision、MinerU Basic、Docling/RapidOCR

旧片段覆盖率只能回答“指定内容能否找到”，不是正确率，不能用1减覆盖率计算CER，也不能据此宣布整体识字冠军。旧结果保留为历史证据

## 研究依据与取舍

通过Exa分别搜索OCR-D质量评估、OmniDocBench评测、阅读顺序与重复输出惩罚，共三组查询，进一步读取以下官方文档/原始论文

- [OCR-D质量评价](https://ocr-d.de/en/spec/ocrd_eval)：GT与识别结果比较，字符以NFC字素处理；识字、分割、阅读顺序、资源消耗分开。本文采用传统CER分母N，不采用OCR-D另一种归一化分母
- [OmniDocBench论文](https://arxiv.org/html/2412.07626v2)与[官方仓库](https://github.com/opendatalab/OmniDocBench)：先提取、匹配，再分别评价文字、表格、公式、顺序。不能直接拿整段Markdown与纯文本比较；当前仓库匹配方法也有版本演进
- [End-to-End Measure for Text Recognition](https://arxiv.org/html/1908.09584v1)：分割和阅读顺序会干扰字符比较，匹配必须约束；忽略顺序的词袋不能充分表示可阅读性

本工程不是上述官方评测工具的复现，不把自己的分数称为OmniDocBench总分。当前没有完整且统一阅读顺序的整页GT，因此不编造整页总CER，也不使用全页字符频次/模糊找子串冒充字符准确率

## 固定的两套输入

1. **识字区域60份**：中文/混排来源40、英文来源20；来源为XFUND、FUNSD、OmniDocBench、ReCTS。固定随机种子20261030，从已有原图按上游框裁剪；问题候选在模型运行前替换，保留修正说明。`data/manifests/recognition60-v3.json`记录参考原文、修正、框和输入SHA256
2. **原整图60份**：继续使用旧基准同一RGB图、长边≤2000、同一SHA256；新跑耗时、错误/空输出和完整结构结果。ESTVQA问答、olmOCR局部断言、无可靠顺序的表单不计整页CER

区域集有字行、段落、竖排、扫描、手写等，全部用各方案当前UI生产配置，不把Rapid切到rec-only。比较的是这些流水线接受已定位文字区域的能力，包含其内部检测/布局误判的影响，不是裸识别模型上限，也不等于整页OCR排名。语言组依据来源页，不是每个区域纯语言标签；提供按汉字脚本的辅助统计

参考沿用上游人工标注并经AI目视复核，不是独立双人校验的金标准。原标注的标点、字宽和拼写可能仍有争议，结果不可外推到所有中文。参考在任何新输出生成前冻结；后续发现问题必须另发版本，不能按引擎结果修改本轮参考

## 计分规则

主指标 **CER = (S + D + I) / N**：S替换、D漏字、I多字；最小Levenshtein编辑距离，保持顺序，重复字符照算插入。对齐最优解可能不唯一，S/D/I的拆分依库确定，总编辑数不变。CER可以超过100%，不裁剪，不笼统写作“准确率=1-CER”

- Unicode先NFC，再按字素簇计数；移除BOM/双向控制符、所有空白，保留大小写、标点、全半角、简繁。主指标名称为**忽略空白CER**，不声称与保留空白的OCR-D得分一致
- 同时输出空白折叠CER（保留单个空格）与文字数字CER（仅Unicode L/N/M），用于识别空格/标点影响，辅助指标不替换主指标
- 中文脚本辅助CER只保留汉字及附属组合符号：用于隔离中文字符，但会忽略字母/数字/标点错误，不能当完整中文文档正确率
- 从结构化节点读取文字：MinerU按pages/blocks/content，Docling按body/furniture引用树、表格cell。图片编码不属于文本；正文真正的`#`、`*`不会被剥除；列表枚举编号、orig中真实存在的符号保留，生成的项目符号不补入；同一引用只读一次，不按文字值去重
- 图中全部参考文字都要比，不只统计出现过的字。表格串行化仅用于保留输出，不宣称其CER代表表格结构质量
- 失败/超时按空文本计全部删除，另报失败数；空结果也计入，禁止只对成功项计算误差
- 汇总采用**微平均**：全组S/D/I求和除以全组N；同时输出每样本CER宏平均、整段完全正确比例、分来源结果
- 同页多个区域不视为完全独立样本；置信区间按父页分组bootstrap（固定种子，2000次），反映当前小样本不确定性，不包含GT系统性误差

## 时间与内存

四引擎顺序运行，各自独立进程，用户级工具环境与全局模型缓存。同一开发图omni-003预热一次，分别记录初始化/预热，随后60区域+60整图顺序处理。报告全部已记录推理秒数，均值/P50/P95只统计成功且有时间的样本，失败/超时耗时另列；未执行耗时为null，中止批次不参与主表速度比较，不混入冷启动时间；进程总墙钟另存。一次运行，不把时间微小差异视为稳定优势

内存采样每50ms求进程及子进程RSS之和，报告观察峰值；可能重复计共享页，也可能漏过瞬时峰值，不等于macOS物理内存压力/Apple GPU完整占用。超24GiB或单图超200秒终止并记录，不能悄悄跳过失败

## 复现

```sh
uv sync
.venv/bin/python -m unittest discover -s tests -v
# 每次选一个不存在的新目录；有任何旧内容都拒绝使用
.venv/bin/python scripts/bench-v3-run.py --run-dir data/outputs/bench-next
.venv/bin/python scripts/bench-v3-report.py --run-dir data/outputs/bench-next
# 只读重评历史输出：独立保存评分版本，不重新运行模型
.venv/bin/python scripts/bench-v3-report.py --run-dir data/outputs/bench-20261030c --report-dir data/reports/rescore-next
```

公开版不包含完整recognition60-v3.json和内嵌研究原文的bench-v3-review.py，以下路径为本机历史证据；复跑前提见[复现指南](reproduce.md)

区域准备与盲审记录：`scripts/bench-v3-prepare.py`、`scripts/bench-v3-review.py`；冻结清单是本轮最终依据。运行worker与Gradio复用同一配置和评分模块`src/ocr_eval/metrics.py`

运行前先完成哈希校验，再独占创建批次目录；reference.json为参考快照，worker通过--run-dir读取该轮inputs.json。报告目录也独占创建，禁止覆盖；不支持隐式续跑。Ctrl-C/SIGTERM清理worker进程组并记录interrupted，未执行样本保留为missing。旧批次没有reference.json时，只读重评仍须通过原冻结参考哈希校验
