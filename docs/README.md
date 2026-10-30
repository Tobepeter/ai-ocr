# 文档导航

客户或新维护者不需要阅读个人任务目录，按以下顺序即可了解项目和复现方式

| 目标 | 文档 |
|---|---|
| 先跑通环境、界面与基准 | [客户复现指南](reproduce.md) |
| 确定哪些文件进Git/交付包 | [Git管理与交付边界](git-policy.md) |
| 看当前技术选型 | [总体选型](ocr-selection.md) |
| 学习已有结论、陷阱和实践 | [OCR经验总结](lessons-learned.md) |
| 理解错误率、时间与内存怎么算 | [评价协议v3.1](ocr-evaluation-v3.md) |
| 安装/复用用户级CLI与缓存 | [CLI说明](cli-setup.md) |
| 使用Gradio与默认示例 | [对比页](ocr-ui.md) |
| 维护项目与测试流程 | [工作流](workflow.md)、[项目约定及参考](project-conventions.md) |
| 了解已发现并修复的问题 | [六项修复记录](review-fixes.md)、[原审查记录](code-review-20261030.md) |
| 复核实测数值与历史比较 | [报告索引](../data/reports/README.md)、[共享数值汇总](../data/reports/shareable/benchmark-v3-summary.json) |
| 了解历史候选和抽样来源 | [方案调研](research/ocr-landscape.md)、[抽样方法](research/ocr-materials.md)、[测试短名单](research/ocr-shortlist.md) |

历史协议benchmark-protocol.md与benchmark-round2.md只解释前两轮，不替代当前协议。详细JSON与逐图原始输出是本地证据，不随默认Git交付；共享汇总不含识别/参考原文
