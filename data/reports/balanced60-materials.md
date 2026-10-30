# 中文优先 60 份 OCR 试评测物料

日期：2026-10-30；冻结版本：`balanced60-v1`。根据用户指定的中文及混排 40 份、英文 20 份完成选样，替代此前“34 试评测 + 8 挑战”的当前运行名单。历史来源记录保留；模型测试后当前输入迁入balanced60-v1，旧批次原图按授权清理

## 实际完成

- 原候选 50 份，新增中文物料 26 份，候选池共 76 份
- 最终选择 60 份，中文及混排 40（66.7%）、英文 20（33.3%），不含原 6 份开发样本
- 新增原图约 21.12 MiB；加 XFUND 来源包和标注约 90.24 MiB。最终 60 份输入约 37.81 MiB；全部 76 份原始输入约 48.19 MiB
- 下载、解码、尺寸/标注检查、视觉筛查和哈希校验已完成；采集当时未运行OCR，随后实测见[模型报告](benchmark-20261030.md)；未逐字复核全部答案

## 最终配比及取舍

| 来源系列 | 中文及混排 | 英文 | 用途与选择依据 |
| --- | ---: | ---: | --- |
| OmniDocBench | 14 | 4 | 多类型文档、表格、公式、混排笔记与竖排；减少原先占比过高的问题 |
| XFUND | 14 | 0 | 官方中文验证划分中固定种子抽样，保险、户籍、招聘、学校申请、公证等表单 |
| ReCTS，经 ChineseOCRBench 获取 | 6 | 0 | 中文招牌文字行裁剪，含低清晰度和特殊字体，用于纯识字 |
| EST-VQA 中文子集，原图来自 LSVT | 6 | 0 | 场景图与问题答案，含远处招牌、电话、店名；作为问答/答案检出专项 |
| FUNSD | 0 | 10 | 已有英文测试表单，排除两份开发样本后全部保留 |
| olmOCR-bench old_scans | 0 | 6 | 旧扫描与手稿断言，排除开发样本并保留不同版面 |
| 合计 | **40** | **20** | 最大单一来源为 OmniDocBench，18/60 = 30% |

按原始来源记为 OmniDocBench、XFUND、ReCTS、LSVT、FUNSD、olmOCR-bench 六个系列。ChineseOCRBench 是 ReCTS/EST-VQA 的打包渠道，不额外算第七个来源。原始文档可能跨基准重叠，因此“六个系列”不代表已经证明六组完全独立

中文文档选入 `omni-001/004/006/009/011/013/014/016/019/024/025/027/029/030`，保留混排、报纸、笔记、繁体和研究报告；移出开发样本、与竖排挑战相近的额外页和正文稀少的试卷页。英文文档选 `omni-002/008/012/028`，覆盖演示、书籍、彩色教材与报告。选择依据是输入内容和用途，未依据模型成绩挑样本

XFUND 使用 `zh.val` 的 50 份候选，固定种子 20261030 抽 14 份；14 份图像均含中文。语言字段保留为 Chinese，不把繁体或双语表单误写成纯简体

街景从固定版本 ChineseOCRBench 的 ESTVQA 709 行、ReCTS 2701 行中分别抽 6 个索引，验证返回的来源字段与缓存图像 revision。这不是原始街景全集的代表性随机样本，仅代表该二次整理子集。索引、原始 ID、问题和上游答案均保留

## 标注与比较边界

- ReCTS 这 6 份是**文字行裁剪**，可以比较行转录；不能说明整图检测能力
- EST-VQA 这 6 份是**场景问答**，不是整图全文答案。传统 OCR 可检查目标答案是否被识出，VQA 可按问答规则评分，两者不能直接混排
- XFUND/FUNSD 具有文字框与实体关系，不默认数组排列就是正确阅读顺序
- OmniDocBench 按原评测格式处理公式、表格和文本，不把含 Markdown/LaTeX 的参考直接当纯文本
- olmOCR 使用局部断言通过率，不能把它与完整转录 CER 混成总准确率
- “60 份”包含页面、表单、场景图和文字行，数量配比只约束来源与语言，不代表相同工作量

## 核验结果

- 最终 60/60 文件及参考均存在，SHA256 各不相同，校验值与采集记录一致
- 新增 26 张图像全部解码，尺寸与上游元数据一致，参考非空；XFUND ZIP CRC 检查通过
- 新增全部图像已看缩略图，原 50 份沿用上一轮视觉筛查；参考仍统一标记 `upstream-not-locally-verified`
- dHash + 长宽比检查未发现近重复候选；这不排除相同模板或原始文档关系，未知分组保留 unknown
- 把一份 EST-VQA 图像及参考移至本地备份后，通过恢复入口重新取回，输入和参考哈希与冻结记录一致
- 重跑选样检查仍为 40/20，原 6 个开发 case_id 与最终名单无交集；旧核验脚本已改为只写历史清单，避免覆盖新的总清单

## 来源调研与访问记录

本轮使用 Exa 搜索三条路径，共请求 15 条结果（含重复），补读数据卡与官方项目。主要来源：

1. [XFUND 官方仓库](https://github.com/doc-analysis/XFUND)与 [v1.0 发布](https://github.com/doc-analysis/XFUND/releases/tag/v1.0)：中文 `zh.val.zip` 为 69,217,820 字节，标注另约 1.6 MiB；官方许可 CC BY-NC-SA 4.0，物料仅本地研究使用
2. [ChineseOCRBench 固定版本数据卡](https://huggingface.co/datasets/SWHL/ChineseOCRBench/blob/857e91af744e05b234c504caf900f932f236de71/README.md)：说明来自 ReCTS 与 EST-VQA。只取单行元数据及缓存图像，没有下载完整打包文件。镜像数据卡的 Apache-2.0 标记不能覆盖上游图片权利
3. [EST-VQA 作者仓库](https://github.com/xinke-wang/EST-VQA)与[原论文](https://arxiv.org/abs/2002.10215)：中文图像来自 LSVT；本项目通过二次整理子集获取，原始 train/test 映射尚未逐项核实
4. [ReCTS 原论文](https://arxiv.org/abs/1912.09641)：招牌识别来源；本轮获取文字行子集，不冒称完整官方测试集
5. [Fudan 中文识别基准](https://github.com/FudanVI/benchmarking-chinese-text-recognition)：作为后续网页/手写候选；包含来自已有街景集的裁剪和合成文档，不能整体算全新独立来源。本轮未拉取其大包

下载中曾遇到 Viewer 502 和大包超时，保持原抽样索引重试，未因下载失败换成其他“好识别”的样本。XFUND 使用断点续传完成；Viewer 临时签名 URL 不写进正式清单。镜像 revision 与缓存 URL 核对一致，但 Viewer API 本身不是固定版本查询接口，未来变化时恢复脚本会拒绝冒充相同数据

## 文件与复现

- [最终 60 份 CSV](../manifests/balanced60.csv) / [冻结名单与核验摘要 JSON](../manifests/balanced60.json)
- [历史76份候选清单](../manifests/materials-history76.csv)
- [中文抽样索引](../manifests/chinese-sampling.json)、[下载及哈希记录](../manifests/chinese-downloads.json)、[来源包校验](../manifests/chinese-resources.json)
- 当前60份在 `data/input/balanced60-v1/`，开发6份在 `data/input/development6-v1/`；原采集批次为历史路径

```sh
python3 scripts/prepare-materials.py --restore
python3 scripts/expand-chinese.py --restore
python3 scripts/select-materials.py
```

采集使用标准库及 curl，选样核验还需 Pillow，旧 PDF 预览由 `scripts/audit-materials.py` 调用 Poppler 生成。全新机器恢复时，在 select 前执行一次该历史核验脚本。恢复入口验证已冻结哈希；若未来上游版本不符，应保留现有物料，不能重新选样后沿用版本号

原图、上游参考、ZIP 包继续本地保存；可纳入 Git 的是脚本、来源与哈希清单、采样决策和本报告。未初始化 Git 或提交

## 下一步

当前先以本 60 份名单开展试评测，早先 120+10 是历史扩充建议，不再作为本轮未完成配额。先用开发样本接通引擎，再复核实际评分字段、按任务分组运行这 60 份

仍缺真实软件截图与独立书写者的系统手写覆盖；六个公开来源也不能证明没有训练重合。本轮无需为补足这些场景立即扩大数量，不把文档/街景结果推广到 GUI 自动化

## 冻结样本表

| case_id | 来源 | 语言组 | 标注类型 |
| --- | --- | --- | --- |
| omni-001 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-002 | OmniDocBench | 英文 | layout-text-table-formula-order |
| omni-004 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-006 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-008 | OmniDocBench | 英文 | layout-text-table-formula-order |
| omni-009 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-011 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-012 | OmniDocBench | 英文 | layout-text-table-formula-order |
| omni-013 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-014 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-016 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-019 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-024 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-025 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-027 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-028 | OmniDocBench | 英文 | layout-text-table-formula-order |
| omni-029 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| omni-030 | OmniDocBench | 中文及混排 | layout-text-table-formula-order |
| funsd-86075409_5410 | FUNSD | 英文 | word-box-entity-relation |
| funsd-82251504 | FUNSD | 英文 | word-box-entity-relation |
| funsd-83573282 | FUNSD | 英文 | word-box-entity-relation |
| funsd-82250337_0338 | FUNSD | 英文 | word-box-entity-relation |
| funsd-85629964 | FUNSD | 英文 | word-box-entity-relation |
| funsd-83641919_1921 | FUNSD | 英文 | word-box-entity-relation |
| funsd-86079776_9777 | FUNSD | 英文 | word-box-entity-relation |
| funsd-87086073 | FUNSD | 英文 | word-box-entity-relation |
| funsd-86328049_8050 | FUNSD | 英文 | word-box-entity-relation |
| funsd-82253245_3247 | FUNSD | 英文 | word-box-entity-relation |
| olm-84 | olmOCR-bench | 英文 | assertions |
| olm-31 | olmOCR-bench | 英文 | assertions |
| olm-55 | olmOCR-bench | 英文 | assertions |
| olm-65 | olmOCR-bench | 英文 | assertions |
| olm-74 | olmOCR-bench | 英文 | assertions |
| olm-67 | olmOCR-bench | 英文 | assertions |
| estvqa-0038 | LSVT | 中文及混排 | question-answer; not full-image transcript |
| estvqa-0225 | LSVT | 中文及混排 | question-answer; not full-image transcript |
| estvqa-0341 | LSVT | 中文及混排 | question-answer; not full-image transcript |
| estvqa-0421 | LSVT | 中文及混排 | question-answer; not full-image transcript |
| estvqa-0558 | LSVT | 中文及混排 | question-answer; not full-image transcript |
| estvqa-0573 | LSVT | 中文及混排 | question-answer; not full-image transcript |
| rects-1214 | ReCTS | 中文及混排 | cropped-line-transcript |
| rects-1781 | ReCTS | 中文及混排 | cropped-line-transcript |
| rects-1815 | ReCTS | 中文及混排 | cropped-line-transcript |
| rects-2826 | ReCTS | 中文及混排 | cropped-line-transcript |
| rects-3130 | ReCTS | 中文及混排 | cropped-line-transcript |
| rects-3308 | ReCTS | 中文及混排 | cropped-line-transcript |
| xfund-zh_val_28 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_25 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_32 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_17 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_47 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_6 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_18 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_13 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_1 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_8 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_49 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_29 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_34 | XFUND | 中文及混排 | text-box-entity-relation |
| xfund-zh_val_4 | XFUND | 中文及混排 | text-box-entity-relation |
