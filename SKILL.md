---
name: office-skills
description: Office 文档技能目录。用户要按 Word 模板编写、重构或修订实验/技术报告时路由到 robot-report-suite；用户要新建、修改、逐页审稿或渲染技术答辩/项目汇报 .pptx 时路由到 technical-defense-ppt。报告与 PPT 使用独立工作区，资料、数据、图片和文本先入燃料目录，再生成版本化初版并渲染微调。
---

# Office Skills Catalog

仅选择一个生产入口：

- `.docx/.pdf` 报告 → `skills/robot-report-suite/SKILL.md`。
- `.pptx` 答辩或项目汇报 → `skills/technical-defense-ppt/SKILL.md`。

不要创建或安装“报告转 PPT”桥接技能。若两种文档都需要，分别建立 `report-workspace/` 与 `ppt-workspace/`；报告和 PPT 只把对方的定稿副本视为只读资料。

## 共同交付顺序

1. 保护模板、原报告、原 PPT 与所有原始资料；不可直接覆盖。
2. 将图片、日志、数据表、代码说明和文字资料放入各自 `input/fuel/`，建立来源与证据台账。
3. 报告先锁定模板保留范围与章节卡片；PPT 先锁定每页结论和版式卡。
4. 输出版本化初版 `v0`，渲染检查后根据反馈输出 `v1`、`v2`……。
5. 只交付通过格式/渲染/证据检查的版本化文件、源图和审计记录。
