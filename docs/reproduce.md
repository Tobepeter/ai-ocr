# 客户复现指南

从项目根目录执行命令。默认目标是macOS Apple Silicon：Apple Vision仅支持macOS，其他平台未完成本项目的端到端验收。不需要个人任务目录、其他参考项目或旧聊天

## 1. 先验证代码与自制样本

准备Python 3.12、uv、Git。使用Apple Vision还需要Xcode Command Line Tools（swiftc）；恢复研究PDF需要Poppler（pdftoppm）。工具不在本项目内分发，可通过各自安装方式准备

```sh
uv sync --frozen
.venv/bin/python -m unittest discover -s tests -v
```

默认环境只有Pillow、rapidfuzz、psutil、regex等轻量依赖，不安装大型OCR模型。首次不恢复研究数据也可以通过单元测试，并使用data/fixtures内两份自制图片及对应reference.txt

## 2. 安装用户级工具与模型

按[CLI安装说明](cli-setup.md)安装固定版本RapidOCR、MinerU、Docling。uv tool安装在用户级隔离环境，不在本项目重复安装模型工具

```sh
.venv/bin/python scripts/prepare-global-models.py
./scripts/ocr-ui.sh
```

prepare-global-models使用RapidOCR官方包初始化缺失的PP-OCRv4 mobile模型，核对configs/rapid-models.json中的SHA256，补齐历史模型名并为Docling建立共享链接。已有文件不一致会失败，不覆盖。MinerU/Docling首次解析时可能另外下载布局与表格模型；确保网络与磁盘空间可用

打开http://127.0.0.1:7861，选择任一自制示例，粘贴该目录reference.txt作为完整参考，开始对比。只有研究数据未恢复时，其他18份示例隐藏是正常现象。两份自制图用于验证链路，不能据此排名真实识字质量

依赖/权重版本影响结果；[模型清单](../data/manifests/model-inventory.json)保留历史模型名、提交号及SHA256，采用可移植缓存标识而非个人绝对路径。它记录历史证据，不会自动下载全部候选模型

## 3. 可选：恢复冻结的研究基准

**公开版前提**：仓库不分发data/manifests/recognition60-v3.json及内嵌原文的历史bench-v3-review.py。下面的派生图恢复和历史基准复跑，需要另行获得允许使用的冻结参考清单并放到该本地路径；仅下载公开仓库不能完整复跑历史60区域成绩。未取得时使用两份自制示例或自己的图片进行界面对比

先阅读[Git与交付边界](git-policy.md)：研究原件与参考存在第三方来源限制，客户功能验收可以直接使用自己的材料，不要求使用这套研究基准

```sh
.venv/bin/python scripts/restore-current.py
.venv/bin/python scripts/restore-derived.py
```

第一步验证或恢复原60份+6份开发材料；第二步按prepared66-v1.json和recognition60-v3.json恢复66张整图及60个文字区域，校验哈希，只写缺失文件。不要重跑旧select-materials或bench-v3-prepare/review来重新抽样或覆盖冻结派生图

上游不可达/镜像版本变化时恢复会失败，不静默换来源；保留错误和哈希，再获取符合分发条件的离线材料包。Pillow/Poppler输出编码或版本差异也可能导致PNG哈希不同，应核对渲染版本，不要把新哈希伪装成旧基准

本机已验证全部126张派生图可以从现存原件在独立临时目录重建并匹配冻结哈希；尚未在另一台全新机器从网络完整恢复所有研究原件

## 4. 开始独立运行

```sh
# 路径必须不存在；每轮换一个名字
.venv/bin/python scripts/bench-v3-run.py --run-dir data/outputs/customer-run-001
.venv/bin/python scripts/bench-v3-report.py --run-dir data/outputs/customer-run-001
```

会依次运行四方案：60文字区域测CER，60原图测时间/空输出。初始化和预热另记；运行目录保存参考快照、输入哈希、版本、原始结果、退出记录和报告。中断清理进程组并保留未完成状态；不要复用旧运行目录

只读重评已有输出时无需重新加载模型：

```sh
.venv/bin/python scripts/bench-v3-report.py \
  --run-dir data/outputs/customer-run-001 \
  --report-dir data/outputs/customer-rescore-001
.venv/bin/python scripts/export-report-summary.py \
  data/outputs/customer-rescore-001/report.json \
  data/reports/shareable/customer-run-001.json
```

详细JSON只留本地；最后一步导出可提交的数值汇总。不同字体、设备、版本、输入和指标不可直接混排

## 5. 读懂结果与排障

- 先看[选型结论](ocr-selection.md)，再看[指标规则](ocr-evaluation-v3.md)和[经验总结](lessons-learned.md)
- 页面“评分不可用”：先看scoring_error，识别文本仍可用；不要当成模型100%错误
- 缺少输入：先恢复原件再恢复派生图，不重选样本
- 缺少模型/路径：核对用户级工具版本、运行prepare-global-models，不重新创建项目模型环境
- 新批次目录已存在：换新路径，不删除旧证据绕过保护
- 不完整报告：检查exit.json/stop_reason与逐引擎日志，缺失不是0秒；当前结果不能参加完整速度比较

项目尚未配置自动CI；此指南说明本地复现，不表示已经部署或授予第三方材料商用权
