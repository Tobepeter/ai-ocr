# Git管理与交付边界

规则按用途和内容划分，不按“输入”或“JSON”一刀切。Git保存复现所需的代码与依据，本机产物和客户原始文件单独存储

| 内容 | 默认处理 | 原因 |
|---|---|---|
| src、scripts、tests、configs | 进入Git | 保留实现、恢复流程、参数与回归 |
| pyproject.toml、uv.lock、依赖版本txt | 进入Git | 固定轻量环境与历史工具版本 |
| README、docs、报告Markdown/数值CSV | 进入Git | 结论、方法、经验、数字证据；CSV仍需确认没有原文 |
| data/reports/shareable/*.json | 进入Git | 显式白名单导出的聚合指标，无识别原文/参考原文/本机命令 |
| data/fixtures | 进入Git | 自制、小型、可分享的输入与正确答案；目前两份合计不足100KiB |
| data/manifests | 条件进入Git | 来源URL、版本、SHA256、冻结选样与裁剪参数；含参考转录的清单须确认交付范围 |
| data/input、references、outputs、models | 不进入Git | 研究/客户原始材料、逐图输出、日志、模型及派生数据；由清单恢复 |
| data/reports下其他JSON | 默认不进入Git | 现有详细JSON混有正文、参考文本、运行命令及个人目录；原文件本地保留 |
| 虚拟环境、缓存、模型权重、external | 不进入Git | 可安装/下载，体积大且与主机环境相关 |
| .temp、本机编辑器配置、密钥、.env | 不进入Git | 个人接力、调试状态和认证信息；仅占位配置示例可以提交 |

## 清单与第三方物料的特别说明

普通来源清单只保存元数据；recognition60-v3.json还包含冻结参考转录及修正记录，是研究基准的必要依据，并不等于纯元数据。它来自第三方公开研究物料，部分表单含姓名、号码等字段。若仓库公开或交付商业客户，应先确认这些转录及来源条款适合交付；没有确认时只交付自制fixtures和客户自己的测试集，不把“公开下载”当成“任意再分发”

现有来源记录中有non-commercial、CC-BY-NC-SA等标记；本工程没有替这些物料重新授权。两份自制fixture用于最小复现，不受研究数据下载状态影响。项目目前也没有设置整体开源LICENSE，Git管理不是对外开源授权

## 为什么不提交所有详细报告

原始data/reports/benchmark-v3.json与benchmark-v3-review-fixes/report.json含逐图reference/plain_text及本机命令。不能仅因文件小于1MiB就默认适合交付。原件不移动、不删除，.gitignore忽略它们；共享指标另存shareable目录

```sh
.venv/bin/python scripts/export-report-summary.py \
  data/reports/benchmark-v3-review-fixes/report.json \
  data/reports/shareable/新的汇总名称.json
```

导出器使用字段白名单，不复制cases、命令和本机路径；目标已存在则拒绝覆盖。它只支持当前v3格式，旧两轮以Markdown与数值CSV为主要共享证据，不把不同指标混合导出

## 交付前核对

1. 查看实际候选文件及忽略情况，确认没有环境、模型、密钥、原始客户材料或详细原文报告
2. 运行轻量测试，按复现指南确认必要文件不依赖个人路径/.temp
3. 交付研究基准时同时审查来源许可与参考转录内容；只交付功能演示时带自制fixture即可
4. 以后文件若已经被Git跟踪，新增ignore不会取消跟踪，应先检查索引再处理；不要用git add -f绕过规则

公开仓库排除recognition60-v3.json及内嵌原文的scripts/bench-v3-review.py，原件留在本地；其余源码、文档、来源元数据、数值汇总和自制示例进入Git。不更改全局Git配置

## 本次审计与重跑

2026-10-30：候选内容约1.05MiB，最大单文件约87KiB；环境、模型、原始输入、输出、详细报告JSON与密钥探针均被忽略，自制示例、锁文件、配置及共享汇总保留。该体积是首次整理时的快照；公开发布已排除研究转录及内嵌原文脚本，最新清单以下方审计结果为准

```sh
.venv/bin/python scripts/audit-git.py --output data/reports/shareable/git-audit.json
```

脚本只在系统临时目录初始化空Git用于匹配忽略规则，退出即清理，不初始化当前工程。候选清单见[审计结果](../data/reports/shareable/git-audit.json)，数量随文件变更而更新；报告不包含自身
