# AI OCR

中文优先的本地OCR实验与对比工程，包含RapidOCR、Apple Vision、MinerU Basic、Docling四方案界面，以及物料恢复、评测和结果导出流程

## 从哪里开始

- **客户/新环境**：[复现指南](docs/reproduce.md)，先用两份随项目保存的自制图片跑通，不必先下载研究数据
- **技术选型**：[总体结论](docs/ocr-selection.md)、[经验总结](docs/lessons-learned.md)
- **Git与交付**：[管理边界](docs/git-policy.md)，代码/配置/锁文件/文档/清单/精简证据可管理，环境/权重/原始输出不提交
- **全部资料**：[文档导航](docs/README.md)、[报告索引](data/reports/README.md)

## 快速验证

```sh
uv sync --frozen
.venv/bin/python -m unittest discover -s tests -v
# 按docs/cli-setup.md安装用户级OCR工具后
.venv/bin/python scripts/prepare-global-models.py
./scripts/ocr-ui.sh
```

浏览器打开http://127.0.0.1:7861，选择自制示例，按对应reference.txt填写完整参考。四方案复用用户级工具和全局模型，不在项目重复安装大型引擎。Apple Vision仅支持macOS

## 已完成与边界

完成两轮九条路线探索、四方案统一CER重评，以及六项项目级审查修复。第三轮四方案各60区域+60原图，共480项；中文/混排与英文区域分别评价，整图另记时间与空输出。没有可靠的整页准确率冠军，也未用文字CER代替表格/公式评价

正式依据：[评价协议](docs/ocr-evaluation-v3.md)、[共享数值汇总](data/reports/shareable/benchmark-v3-summary.json)、[修复记录](docs/review-fixes.md)。旧报告保留当时口径；覆盖率不等于准确率，裁剪区域结论不外推整页

## 目录

```text
src/、scripts/、tests/    实现、恢复/评测工具与回归
configs/                 固定配置、模型哈希、示例清单
docs/                    复现、选型、方法、经验与维护说明
data/fixtures/           两份自制小样本与参考，可随Git保存
data/manifests/          来源、哈希、冻结样本及派生恢复清单
data/reports/shareable/  可分享的聚合JSON；报告Markdown/数值CSV另存reports
data/input/、outputs/    本地原件与机器输出，不提交
.temp/                   个人接力与临时材料，不是客户复现依赖
```

公开版不包含研究参考转录recognition60-v3.json及内嵌原文的历史盲审脚本，完整历史基准需另行获得可用的参考清单；自制示例与基础测试可直接使用。尚未配置CI；公开仓库不自动授予第三方数据或模型再分发权
