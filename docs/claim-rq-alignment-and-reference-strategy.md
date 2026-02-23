# Claim-RQ 语义对齐与引用结构策略：问题分析与工程方案

> 更新说明：本文聚焦 A+D 策略子集。最终工程收敛与不回归执行顺序请以 `docs/final-no-regression-remediation-plan.md` 为准。

## 1. 背景与目标

在运行 `outputs/run_20260222_222740`（时间戳：2026-02-22 22:43:30）中，`claim_evidence_support` 已通过（每个 RQ 至少 2 条证据），但仍出现：

- `claim_rq_relevance: warn`（claim 与 RQ 词面相关度不足）
- `reference_domain_profile: warn`（非学术域名比例偏高）

目标是在不降低标准的前提下，让验收结果从 `warn` 提升到稳定 `pass`，并保持工程可维护性。

## 2. 现状问题定位（代码层）

### 2.1 Claim 与 RQ 对齐不足

现状：

- claim 候选主要来自 source 的 `key_findings/summary`，偏“论文原句”而非“RQ问法”。  
  代码：`src/agent/nodes.py:_claim_candidates`。
- 是否有 RQ 信号仅做布尔交集，不保证足够覆盖。  
  代码：`src/agent/nodes.py:_claim_has_rq_signal`。
- 验收侧用词面覆盖率（交集占比）判定，阈值 0.20；长 RQ 容易告警。  
  代码：`scripts/validate_run_outputs.py:_claim_relevance_ratio`。

结论：生成侧与验收侧口径不一致，导致“语义相关但词面不够”被判 warn。

### 2.2 引用结构策略不清晰

现状：

- 验收脚本会扫描报告中所有列表 URL，非学术域名计入比例。  
  代码：`scripts/validate_run_outputs.py:extract_reference_urls`。
- 报告中实验蓝图的 `Datasets` 常含 GitHub/UCI 链接，容易拉高非学术比例。  
- 实际上这些链接是“数据资源”，不应与“论证证据”完全同权。

结论：当前“引用结构”没有区分证据引用与资源引用，导致指标噪声。

## 3. 可选方案与利弊

## 3.1 Claim-RQ 对齐

### 方案 A：模板化 claim 重写（推荐）

做法：

1. 在 claim 生成后做一次 deterministic 重写：  
   `claim = "Regarding <RQ锚点术语>, evidence suggests <原claim核心>"`。  
2. 锚点术语取 RQ 的高信息词（去停用词，取 2-4 个）。

优点：

- 不增加额外 LLM 调用，成本低。  
- 可直接对齐验收的词面规则。  
- 可控、可测试、可回滚。

缺点：

- 语言风格可能略模板化。  
- 多语言场景需要额外模板（en/zh）。

---

### 方案 B：再走一次 LLM 语义改写

优点：

- 语句自然，语义贴合更强。  

缺点：

- 增加 token 成本和失败面（模型随机性、速率限制）。  
- 结果不稳定，不利于自动化验收。

---

### 方案 C：降低验收阈值

优点：

- 快速消除告警。  

缺点：

- 牺牲标准，不解决根因。  
- 长期会弱化报告质量约束。

## 3.2 引用结构策略

### 方案 D：按“用途”分层引用（推荐）

做法：

1. `References` 仅放“论证证据引用”（papers/DOI/arXiv）。  
2. 数据集/代码仓库/文档链接放在 `Experimental Blueprint` 的 `Datasets/Resources`，但不进入证据引用预算。  
3. 验收脚本中 `reference_domain_profile` 仅统计 `References` 段落内 URL。

优点：

- 指标语义清晰，减少误报。  
- 不损失实验可复现信息。  
- 与“证据链”概念一致。

缺点：

- 需要调整解析逻辑与测试用例。  
- 旧报告与新报告统计口径不一致（一次性迁移成本）。

---

### 方案 E：保留现状，仅扩大学术域名白名单

优点：

- 改动最小。  

缺点：

- 把资源域名硬塞到学术域名集合，语义不准确。  
- 长期维护成本高，规则会越来越脏。

## 4. 推荐的最优工程策略（综合）

采用 **A + D** 的组合方案：

1. **生成侧收敛（A）**：claim 轻量模板化对齐 RQ 锚点词，确保通过 `claim_rq_relevance`。  
2. **结构侧收敛（D）**：引用分层，`References` 只统计证据引用；资源链接不参与证据域名比例。

为什么这是最优：

- 质量不降级：不放松验收阈值。  
- 成本可控：不新增 LLM 回合。  
- 可测试性强：确定性逻辑 + 单测可覆盖。  
- 与现有架构兼容：改动点集中在 `nodes.py` 与 `validate_run_outputs.py`。

## 5. 最小落地改造清单

### Step 1（生成侧）

在 `src/agent/nodes.py` 增加 `claim 对齐器`：

- 输入：`rq`, `claim`。  
- 逻辑：若词面相关度 < 阈值（例如 0.20），执行模板重写并保留原 claim 语义。  
- 输出：对齐后的 claim。

建议新增配置：

```yaml
agent:
  claim_alignment:
    enabled: true
    min_rq_relevance: 0.20
    anchor_terms_max: 4
```

### Step 2（引用结构）

在 `scripts/validate_run_outputs.py` 调整 URL 提取逻辑：

- 仅在 `## References`（或 `## Bibliography`）章节内提取“证据引用 URL”；  
- 不再把 `Experimental Blueprint` 里的 dataset/resource URL 纳入 `reference_domain_profile`。

### Step 3（测试）

新增/更新测试：

1. claim 重写后 `claim_rq_relevance` 提升到阈值以上。  
2. dataset URL 出现在实验蓝图时，不影响 `reference_domain_profile`。  
3. `References` 内非学术链接仍能被正确告警（防止规则失效）。

## 6. 风险与回滚

风险：

1. claim 模板化导致文字重复感增强。  
2. References 解析口径变化导致历史结果不可横向比较。

回滚：

1. `agent.claim_alignment.enabled=false` 关闭对齐器。  
2. 保留旧解析函数，按配置切换 `strict_reference_parsing`。

## 7. 预期结果

在不降低标准的前提下，预期：

1. `claim_rq_relevance` 从 warn 降到 pass（或显著减少）。  
2. `reference_domain_profile` 从“被资源链接污染”转为“仅反映证据引用质量”。  
3. 整体验收从 `overall: warn` 稳定向 `overall: pass` 收敛。
