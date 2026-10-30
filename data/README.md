# 物料与结果管理

原始物料是实验依据，按用途、体积和可再分发条件决定存储位置，不一律忽略。已采集 76 份候选，当前选择 60 份，见 [中文优先选样报告](reports/balanced60-materials.md)，参考尚未逐字人工校对

| 位置 | 内容 | Git |
| --- | --- | --- |
| `fixtures/{case_id}/` | 小型原始图片/PDF、人工答案、必要的来源说明 | 可以提交，建议单文件不超过 1 MiB；较大文件单独评估 |
| `manifests/` | 所有实验样本的来源、哈希和恢复信息 | 提交，私有来源只写可共享的标识，不含凭据 |
| `input/` | 大型、批量或私有原始样本 | 忽略，通过清单恢复 |
| `references/` | 大批量或私有人工答案 | 忽略；小型公开答案随 fixture 保存 |
| `outputs/` | 原始机器结果、派生图片、日志 | 忽略 |
| `reports/` | Markdown、数值CSV与shareable下聚合JSON | 可以提交；其他详细JSON默认忽略，保留本地 |

## 清单字段

[materials.csv](manifests/materials.csv) 每行一个 case_id，路径相对项目根目录。多页文档可用不同 case_id 和 page 字段指定页码（从 1 开始），同一文件共享 SHA256

- `case_id`、`task`、`language`：稳定标识、输出目标与语言
- `input_path`、`page`、`sha256`：输入位置、可选页码与原始文件校验值
- `source`、`revision`、`license`：来源 URL/自制说明、数据集版本、再分发依据
- `reference_path`、`reference_status`：答案位置与 `pending` / `reviewed` 状态
- `storage`、`restore`：`git` / `local`，以及下载命令、脚本或人工恢复说明

缺少原始文件的旧截图实验保留为历史观察，不编造清单条目或性能数字。原始物料保持不变，预处理参数和派生产物记录在对应运行目录。人工答案可修订，但比较时记录所用 Git 提交或答案哈希

私有图片及答案均留本地；可共享报告也需检查是否含原文。凭据不得写入来源 URL。后续发现需要大规模共享原始物料时再确定外部存储或 Git LFS，目前未配置

## 多来源与抽样

正式采集按 [OCR 来源与抽样方案](../docs/research/ocr-materials.md) 执行。清单新增来源追溯与分组字段：

- `dataset_id`、`source_item_id`、`source_split`：原始数据集、样本 ID 和上游划分，镜像不另计来源
- `stratum`、`document_id`、`template_id`、`site_id`、`writer_id`：场景层和独立性单位，不适用留空，未知填 unknown
- `group_id`、`eval_split`：开发/留出隔离组，以及 development / pilot-evaluation / challenge / exploratory / sparse-text；正式独立留出另用 holdout；不能把同一文档不同页随机拆开
- `annotation_type`、`reference_sha256`：完整转录、版面框、结构或断言等答案类型及校验值，不能混用评分
- `parent_case_id`、`synthetic`、`sampling_seed`：派生关系、是否合成（true/false）、抽样种子

候选元数据和抽样规则同样是复现资产，应保存可共享的快照或固定版本及恢复脚本；历史采集清单含76份候选，当前总清单只保留60份，当前采用 balanced60.csv 的 40 中文及混排 + 20 英文；120+10 是历史扩充建议

当前总清单另含 `original_source` 与 `language_group`，用于避免把镜像算成独立来源；`eval_split` 的 reserve 表示未进入本轮名单。当前名单已冻结，勿重新运行历史select-materials.py覆盖路径；当前目录整理由consolidate-materials.py维护，pilot/chinese清单保留历史采集来源

## 当前保存与恢复

正式输入和参考位于input/balanced60-v1，开发6份单独位于input/development6-v1，不参与主测试指标。运行`python3 scripts/restore-current.py`验证/恢复全部66份；缺失时按冻结来源重建历史采集包，校验迁移后自动删除中间批次。参考清单和来源包哈希保留，原始内容不因重组改变

历史采集脚本prepare-materials.py、expand-chinese.py、select-materials.py用于解释最初76份来源；正常复跑不需要重新选样。恢复已做本地哈希路径验证和早期单份下载验证，尚未在另一台机器全量重建

## v3识字区域集

冻结清单为manifests/recognition60-v3.json，含原图父ID、裁剪框、AI目视复核修正、上游参考原文与SHA256。中文/混排40、英文20，总60区域，来自原60份的子集页面，并不替代原整图集。裁剪在模型运行前冻结，参考不是独立双人校验金标准。历史生成记录为scripts/bench-v3-prepare.py与scripts/bench-v3-review.py；恢复用scripts/restore-derived.py从冻结清单重建，不重新随机选样

客户入口：[复现指南](../docs/reproduce.md)、[Git边界](../docs/git-policy.md)。recognition60-v3.json含第三方参考转录，不只是来源元数据，公开/商业交付前应确认分发范围；自制fixtures可用于不下载研究集的最小演示
