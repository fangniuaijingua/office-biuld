---
name: technical-defense-ppt
description: 唯一用于创建、重构、审稿和渲染技术答辩、项目汇报与毕业设计 PowerPoint 的技能。用户要求制作、修改、优化或审查 .pptx 时使用；可直接读取原始素材或已定稿报告，不撰写 Word/实验报告正文。
---

# 技术答辩 PPT

## 职责边界（优先执行）

- **这是唯一的 PPT 生产入口**：凡是新建、改版、审稿、渲染、讲稿或答辩演示 `.pptx`，均在此技能和 `ppt-workspace/` 内完成。
- 已定稿报告是可选只读输入；直接提取其内容和证据即可。不要要求用户先运行“报告转 PPT”桥接技能，也不要创建额外桥接工作流。
- 若用户同时要求 Word 报告和 PPT，先分别锁定两个独立工作区：Word 用 `robot-report-suite`，PPT 用本技能；任何一方不得改写另一方的输出。
- 不创建、修改、重排或清理 Word 报告；报告修订一律交回 `robot-report-suite`。

本技能是独立的 PPT 生产包。它只创建或审查 `ppt-workspace/` 中的 PPT 工件；不会要求先写报告，不会读取或改写 Word 模板、报告正文、摘要、报告 `manifest.json` 或原始证据文件。

## 先选一种模式

每次任务只选择下列一种入口，避免把无关工作流混入本轮：

1. **独立新建**：用户给原始照片、日志、图表、主题或已确认事实；先产出 brief、资产清单和页面计划。
2. **既有 PPT 改版**：用户给 `.pptx`、截图、保留内容和风格参考；先保护输入副本并渲染基线。
3. **报告导入**：用户提供只读报告或桥接包；只读取 `report-handoff.md`，将证据映射为页面，不改写报告。
4. **视觉审稿**：用户提供幻灯片截图、设计参考或成品；只输出审美诊断、token、版式规则和可执行改版清单，不虚构项目事实。

没有报告也能完整执行。没有实测材料时，只能交付设计方向、占位结构和一次性缺料清单，不能虚构性能、验收或现场部署证据。

## 独立边界

1. 只使用本技能 `references/` 内的规则；不要依赖其他 Skill 的内部证据文件、Word 工具链或章节规则。
2. 所有结论按 `references/evidence-boundary.md` 回链 Asset ID、数据版本和条件；外部/生成图只能承担情境或解释层，并在资产清单中标明生成/原始、用途与限制。
3. 流程图、曲线和拓扑按 `references/editable-visuals.md` 保留可编辑源；不要把截图作为唯一源文件。技术流程树默认采用黑白可编辑图，可与真实或明确标注为解释用途的彩色图像组合。
4. 输入、输出和渲染均存于独立 `ppt-workspace/`；不可覆盖用户给出的 `.pptx`。
5. 仅在用户明确提供报告或桥接包时，才读取 `references/report-handoff.md`；报告是可选输入，不是前置条件。

## 推荐工作区

```text
ppt-workspace/
  input/original/        # 原 PPT、报告副本与哈希/只读说明
  input/fuel/            # 图片、视频帧、日志、数据表、代码说明和文字资料
  brief/                 # 受众、时长、主线、问答目标和限制
  assets/                # 资产清单、关键帧、权属与证据边界
  page-locks/            # 单页结论、裁切、Hero/Support/Finish
  source/                # 可编辑图表、拓扑、讲稿和 PPT 源
  output/                # 版本化 .pptx/.pdf，绝不覆盖输入
  preview/               # 最近三个可丢弃预览版本
  render/                # 单页渲染图与全套 contact sheet
  qa/                    # 结构检查、评分、修订记录
  notes/                 # 讲述节拍、证据回指和 Q&A
  handoff/               # 可选报告导入的只读交接包
```

## 生产顺序

### 阶段 A：输入保护与事实盘点

从 `input/` 的副本开始，记录文件名、大小、修改时间和哈希。建立 Asset ID；先写清每项素材能证明与不能证明什么，再确定页面数量和叙事主线。

### 阶段 B：页面锁定

将未加工的图片、日志、数据表和文字资料放在 `input/fuel/`，在 `assets/` 建立资产台账后再确定页面。按 `references/page-lock-template.md` **按页序**锁定每页结论、证据等级、Hero、Support、Finish、版式模式、相邻页差异和讲解节拍。内容页没有锁定卡不得进入排版。

### 阶段 C：视觉系统、图像组合与可编辑图源

按 `references/design-language.md` 先建立 16:9 母版、色彩 token、网格、字阶和页面语法；按 `references/visual-mix-and-finish.md` 为每页指定彩色实物/情境图、黑白技术图与有功能的 Finish；按 `references/editable-visuals.md` 制作可编辑拓扑/图表。先校准封面、最难技术页、最强验证页三张；1—3 页短 deck 使用生产系统中的例外。

### 阶段 D：构建、渲染与返工

按锁定卡的页序逐页制作，先输出可渲染的 `v0`，再按 `references/render-delivery.md` 导出单页和 contact sheet，并按 `references/review-rubric.md` 审稿。每轮微调输出 `v1`、`v2`……，不覆盖原 PPT 或上一确认版。先纠正结论、边界和证据，再处理阅读路径、裁切和材质，最后才加 Finish。

### 阶段 E：交付

仅在 `references/validation-plan.md` 的 G0—G4 通过后交付版本化 `.pptx`、可编辑图源、资产清单、页面锁定卡、渲染图、审稿记录和讲述备注。

## 参考文件

- `references/evidence-boundary.md`：独立证据等级、事实边界与可比性规则。
- `references/asset-manifest-template.md`：资产、视频、页面映射和缺料队列。
- `references/page-lock-template.md`：每页结论、Hero/Support/Finish 与豁免规则。
- `references/design-language.md`：色彩、网格、字阶、裁切、视觉语法和反模式。
- `references/visual-mix-and-finish.md`：彩色图、黑白技术图、生成图及页面修饰元素的组合规则与提示词骨架。
- `references/editable-visuals.md`：流程图、拓扑、曲线与源文件交付规则。
- `references/production-system.md`：资产先行、三页校准、逐页渲染生产门。
- `references/render-delivery.md`：输入保护、渲染、视频备份和交付目录。
- `references/review-rubric.md`：100 分审稿量表、硬失败和返工顺序。
- `references/validation-plan.md`：G0—G4 质量门与前向测试。
- `references/report-handoff.md`：仅在导入报告时使用的单向交接规则。
