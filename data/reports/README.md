# OCR报告索引

客户优先阅读Markdown、数值CSV和shareable聚合JSON。其他详细JSON含原文或本机路径，已默认忽略；历史报告里指向这些JSON的链接是本地完整证据入口，Git副本未必包含

## 当前依据

- [第三轮报告](benchmark-v3.md)：四方案各60文字区域+60整图，CER、S/D/I、耗时、内存及限制
- [修复后只读重评](benchmark-v3-review-fixes/report.md)：480条旧输出重新提取/评分，区域主表未变，不是重新运行模型
- [共享数值汇总](shareable/benchmark-v3-summary.json)：保留分组指标、版本、资源与哈希，不含正文/参考/个人命令
- [共享修复验证](shareable/review-fixes.json)：六项修复与验证摘要
- [总体选型](../../docs/ocr-selection.md)、[客户复现指南](../../docs/reproduce.md)

## 历史研究

- [第一轮CPU路线](benchmark-20261030.md)：RapidOCR、PaddleOCR、Tesseract、EasyOCR、Docling各60份
- [第二轮扩展](benchmark-round2.md)：Apple Vision、GLM、PaddleOCR-VL、MinerU各60份，另补Tesseract内存
- [60份选样](balanced60-materials.md)、[首批筛查](pilot-materials.md)
- requirements-*.txt保留历史依赖约束；不代表所有工具当前都应安装

原始报告不随迁移或修复改写成绩。新跑/重评使用新目录；共享JSON用scripts/export-report-summary.py白名单导出。详细结果与运行日志留在本地或另行约定的受控材料包，不执行无差别Git提交
