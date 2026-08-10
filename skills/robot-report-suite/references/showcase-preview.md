# 报告效果展示预览

当用户需要查看报告的视觉效果、逐页图片或联系表时，预览必须从已定稿并通过格式审计的 PDF 派生。预览只说明排版与可读性，不替代可编辑报告，也不产生新的实验结论。

## 目录和命名

```text
report-workspace/
  output/
    project-report_v8.docx
    project-report_v8.pdf
  qa/
    template-style-v8.json
  showcase/
    v8/
      page-01.png
      page-02.png
      contact-sheet.png
      preview-manifest.json
```

`preview-manifest.json` 至少记录：来源 PDF 相对路径、SHA-256、页数、渲染时间、页图列表和用途（`layout_preview` 或 `presentation_reference`）。预览目录必须与 `qa/` 分开；版本号必须与来源报告相同。

## 生成与检查

1. 仅以 `output/` 中的最终 PDF 为输入；先确认该 PDF 对应的 `.docx`、格式审计和保护页检查均通过。
2. 使用 `scripts/render_report_showcase.py --input <final.pdf> --output report-workspace/showcase/vN` 导出每页 PNG、联系表和预览清单；不要以截图软件临时截图替代可追溯输出。
3. 联系表不裁切、不改变页面顺序；封面、基础信息页、复杂表格和最后一页必须单独目视检查。
4. 展示重点页时，使用原始页图，不把多页内容拼接为看似单页的图；任何裁切都要标注“局部预览”。
5. 用户反馈版式问题时，回到版本化 `.docx` 修订并重新导出 PDF；禁止在 PNG 上修图后把它当作报告修订。

## 与 PPT 和公开仓库的边界

- PPT 仅可把最终 PDF 或已登记的展示 PNG 当作只读资料；PPT 的页面规划和生产仍由 `technical-defense-ppt` 负责。
- 公开技能仓库只能提交此规则、脚本和无敏感占位结构；不得提交任何用户的报告、页面 PNG、联系表、照片、日志、模板或真实项目数据。
