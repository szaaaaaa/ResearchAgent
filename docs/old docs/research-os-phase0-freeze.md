# Research OS Phase 0 冻结文档

> 日期：2026-03-08
> 范围：只冻结 `3-agent literature review MVP` 的边界、接口和兼容要求

## 1. 目标

Phase 0 不实现新能力，只做 5 件事：

1. 冻结 MVP 范围
2. 冻结第一批 artifacts
3. 冻结第一批 skills
4. 冻结 `LLMProvider` 最小接口
5. 冻结迁移期间 CLI 兼容边界

---

## 2. MVP 范围

本轮 MVP 只覆盖：

1. `Conductor`
2. `Researcher`
3. `Critic`

本轮只跑通：

1. topic intake
2. literature search
3. paper parsing
4. paper notes extraction
5. related work synthesis
6. gap analysis
7. critique / revise / pass

本轮明确不做：

1. `Writer`
2. `Experimenter`
3. `Analyst`
4. code generation
5. experiment running
6. result analysis
7. full paper writing

---

## 3. 第一批 Artifacts

Phase 0 冻结如下 7 个 artifact：

1. `TopicBrief`
2. `SearchPlan`
3. `CorpusSnapshot`
4. `PaperNote`
5. `RelatedWorkMatrix`
6. `GapMap`
7. `CritiqueReport`

最小字段约束：

- `artifact_type`
- `artifact_id`
- `producer`
- `source_inputs`
- `payload`
- `created_at`

---

## 4. 第一批 Skills

Phase 0 冻结如下 6 个 skill：

1. `search_literature`
2. `parse_paper_bundle`
3. `extract_paper_notes`
4. `build_related_work_matrix`
5. `map_research_gaps`
6. `critique_related_work`

这些 skill 的职责边界固定如下：

1. `search_literature`
   - 输入：`SearchPlan`
   - 输出：`CorpusSnapshot`
2. `parse_paper_bundle`
   - 输入：`CorpusSnapshot`
   - 输出：更新后的 `CorpusSnapshot`
3. `extract_paper_notes`
   - 输入：`CorpusSnapshot`
   - 输出：`PaperNote[]`
4. `build_related_work_matrix`
   - 输入：`PaperNote[]` + `SearchPlan`
   - 输出：`RelatedWorkMatrix` + `GapMap`
5. `map_research_gaps`
   - 先视为 `build_related_work_matrix` 的子能力，不单独拆实现
6. `critique_related_work`
   - 输入：`CorpusSnapshot` + `RelatedWorkMatrix` + `GapMap`
   - 输出：`CritiqueReport`

---

## 5. 当前代码映射

Phase 0 只确认映射，不改实现：

1. [planning.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/planning.py)
   - 提供 `TopicBrief` + `SearchPlan`
2. [retrieval.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/retrieval.py)
   - 对应 `search_literature`
3. [indexing.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/indexing.py)
   - 对应 `parse_paper_bundle`
4. [analysis.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/analysis.py)
   - 对应 `extract_paper_notes`
5. [synthesis.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/stages/synthesis.py)
   - 对应 `build_related_work_matrix` / `map_research_gaps`
6. [retrieval_reviewer.py](/c:/Users/ziang/Desktop/ResearchAgent/src/agent/reviewers/retrieval_reviewer.py)
   - 对应 `critique_related_work`

---

## 6. LLMProvider 最小接口

Phase 0 冻结如下 provider 接口，不在本阶段落代码实现：

```python
class LLMProvider(Protocol):
    def generate(self, request: ModelRequest) -> ModelResponse: ...
    def stream(self, request: ModelRequest): ...
    def call_tools(self, request: ToolCallRequest) -> ToolCallResponse: ...
```

兼容目标固定为：

1. `Gemini 3 Pro`
2. `ChatGPT 5.4`
3. `Claude`

冻结要求：

1. role 不直接调用具体 SDK
2. skill 不直接绑定具体 provider
3. artifact 不包含 provider 专有字段

---

## 7. CLI 兼容边界

迁移期间 CLI 兼容要求固定如下：

1. 现有 CLI 入口继续保留
2. 现有 run outputs 继续保留
3. Phase 0 不改默认运行路径
4. Phase 1 之后允许增加 artifact sidecar 输出
5. 新 Research OS 路径未来通过独立模式接入，不直接覆盖 legacy 流程

---

## 8. Phase 0 Definition Of Done

Phase 0 完成的标准只有这些：

1. 3-agent MVP 边界不再变化
2. 第一批 artifact 清单固定
3. 第一批 skill 清单固定
4. `LLMProvider` 最小接口固定
5. CLI 兼容边界固定

如果以上 5 项没有全部冻结，就不进入 Phase 1。
