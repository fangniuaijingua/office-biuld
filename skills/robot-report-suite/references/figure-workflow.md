# 图形工作流：create-figure 适配版

本规则参考 [create-figure](https://github.com/grahama1970/agent-skills/tree/main/skills/create-figure) 的多后端和数据溯源思想，并以官方 [Draw.io MCP/CLI Skill](https://github.com/jgraph/drawio-mcp/tree/main/skill-cli/drawio) 的 `.drawio` 作为流程图与结构图源格式。这里去除了上游私有/未安装服务；这是工作流参考，不是任一仓库代码的副本。

## 图形证据门（先于绘制）

每幅图先填写以下卡片。若“数据/事实来源”为空，只能画明确标注为“设计示意”的图，不能画成实测结果。

```yaml
id: fig_3_2
purpose: 要让读者理解的一个结论
kind: flow | topology | sequence | state | signal | chart | photo_annotation
facts_or_data: 文件路径、日志范围、代码符号或用户确认
evidence_status: measured | user_confirmed | design_schematic | pending
requested_backend: auto | graphviz | mermaid | matplotlib
required_labels: 单位、接口名、图例、测试条件
output: figures/export/fig_3_2.svg
style_contract: template_style | monochrome_black_white
```

## 本地后端路由

| 图形任务 | 首选 | 回退 | 必须保留 |
| --- | --- | --- | --- |
| 硬件组成、端口关系、数据流 | Draw.io | Graphviz（若已安装） | `.drawio` 与嵌入 XML 的 SVG/PNG |
| 控制流程、蓝牙状态、动作步骤 | Draw.io | Mermaid | `.drawio`/`.mmd` 与 SVG |
| UART 请求/响应、动作时序 | Draw.io sequence | Mermaid sequence | 源文件与 SVG |
| PWM、转角、姿态、LADRC 观测、响应曲线 | Matplotlib | 无 | `.py`、原始 CSV/日志摘录、SVG/PNG |
| Bode/Nyquist/根轨迹 | Matplotlib + 已验证模型参数 | 明确标注为仿真 | 脚本、模型参数、SVG/PNG |
| 实物接线或测试过程 | 用户原始照片 | 标注图 | 原图、标注版本、图注 |

## 生成与验收

1. 提取图形目的、输入文件、数值单位和证据状态；缺少实测数据时停止在图形卡片，不猜测数值。
2. 选择最简单且可编辑的后端；有 Draw.io 时，流程/结构图保存 `.drawio`。不使用位图“画图”代替可编辑源。流程/结构/曲线默认导出白底黑白图，节点和箭头使用形状、编号、实/虚线表达语义；少量彩色实物/相机证据图片按 `visual-color-policy.md` 单独登记，不能承担流程语义。
3. 生成导出物时统一保存 `SVG + PNG`；Draw.io 导出使用嵌入 XML 的模式；曲线类还保存脚本和数据摘录。
4. 检查：标题、中文字体、箭头方向、接口名、坐标单位、图例、编号和图注是否一致。
5. 插入 Word 前，将图题、源文件、证据状态写入 `manifest.json`；布局由 OfficeCLI/Word 副本负责。

## 禁止事项

- 不从未提供的数据推断“实测波形”“性能曲线”或具体数值；
- 不因报告好看而删去测试条件、单位或数据来源；
- 不直接修改原始 `.doc` 模板；
- 不把 Office 文档内的截图当作唯一图源；
- 不按上游 Draw.io 示例在导出后删除 `.drawio` 源文件。
- 不把演示型彩色信息卡片、渐变或装饰背景带入 Word 论文图；模板已有的官方图标与已登记的少量彩色证据图片除外。
