# PPT 图像组合与修饰层

## 1. 先分角色，再决定颜色

每页把视觉资产分为下列四类，并登记 Asset ID；不能为了“页面丰富”交换角色。

| 角色 | 可用材料 | 推荐色彩 | 可承担的结论 |
| --- | --- | --- | --- |
| Hero | 项目实拍、视频关键帧、真实界面/数据 | 保留原始彩色，统一裁切与明度 | 实物、场景、动作或已记录现象 |
| 技术 Support | 流程树、通信拓扑、状态机、量化图表 | 默认黑白/灰阶，可编辑 | 机制、接口、条件、回退逻辑 |
| 解释图 | 代码生成图、外部参考或 AI 生成图 | 可少量彩色，必须显式标注 | 背景、概念或视觉解释，非实测 |
| Finish | 页码轨、图注轨、裁切框、测量刻度、低透明轮廓 | 中性色或单一 token | 导航、框定、节奏或深度，不承担事实 |

常规技术页优先采用“一个彩色 Hero + 一个黑白技术 Support + 一至两类 Finish”。彩色 Hero 通常占视觉面积 35%—60%，黑白 Support 约 20%—40%；当没有真实彩色图时，宁可采用白底技术页，也不要用生成图冒充实拍。

## 2. 生成图的安全用法

仅在缺少情境/解释素材时才调用 `imagegen` 生成位图；不要用它生成流程图、精确线路图、数据曲线、带文字界面的截图或任何应由代码/矢量工具制作的技术图。生成图在资产清单与图注中写为“生成解释图，非实测”，不承载性能、验收或现场部署结论。

建议提示词骨架：

```text
Use case: scientific-educational or product-mockup
Asset type: technical defense PPT explanation insert
Primary request: <仅描述概念场景/对象，不描述未证实的实验结果>
Composition/framing: <为标题或黑白流程树预留的方向与负空间>
Color palette: <与 PPT token 协调的低饱和原色；不抢主证据>
Text: none
Constraints: conceptual explanatory image only; no logos, dashboard text, measurements,
test results, watermark, or claims of real-world deployment
```

生成后检查主体、文字、读数和标识；只要出现会被误认的实验信息，就丢弃或重生成。把最终图复制进 `ppt-workspace/assets/`，同时在 manifest 写明生成工具、提示词、日期、用途和“不可证明”的范围。

## 3. 黑白流程树的交付

流程、状态、通信和故障恢复优先用 Graphviz/Draw.io/Mermaid 生成。白底、黑字、黑线、灰色辅助线；用标签、形状、线型和编号表达分支，不以红绿黄状态卡作为唯一编码。

```powershell
python "<skill-dir>\scripts\render_graphviz_asset.py" `
  --input "ppt-workspace\source\mission-flow.dot" `
  --out-dir "ppt-workspace\assets\generated" --monochrome
```

保留 `.dot`、SVG、PNG 与命令记录。PPT 中可把树图置于白色信息区，并与彩色照片保持清晰的边界；不要把树图压在复杂照片上。

## 4. Finish 元素库与预算

Finish 是可重复的版式语法，不是任意贴纸。每页从以下类别选择不超过两类：

| 类别 | 合理用途 | 禁止用途 |
| --- | --- | --- |
| 导航轨 | 页码、章节索引、Asset ID、来源条件 | 装饰性长句、无意义坐标 |
| 框定线 | Hero 裁切框、局部放大连接、图注引线 | 厚边框包围所有对象 |
| 工程刻度 | 接口方向、步骤编号、尺寸/时间条件 | 伪造量测或数据精度 |
| 低透明轮廓 | PCB、机架、路线等项目相关纹理 | 无关芯片、地球、粒子背景 |
| 分隔/底纹 | 两种阅读区的轻量区分 | 渐变大色块、重复圆角卡片墙 |

Finish 合计通常不超过页面视觉面积的 10%，只用单一强调 token 或中性灰。每个元素都要在 Page Lock 写下它服务的“定位、框定、节奏、深度”之一；说不出作用就删除。若 Hero 已经复杂，则删去纹理，只保留来源轨和一条框定线。

## 5. 审稿提问

1. 去掉彩色 Hero 后，黑白技术图还能否解释机制和边界？
2. 去掉 Finish 后，本页是否仅损失导航/节奏而非事实？若损失事实，说明把信息错放在装饰层。
3. 生成图是否有清晰的“非实测”身份，并且没有压过项目证据？
4. 三秒能否读到结论、十秒能否发现 Hero、技术 Support 与来源条件？
