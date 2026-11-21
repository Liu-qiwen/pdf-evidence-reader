# 科研 PDF 阅读与证据定位

版本 1.0.0。适用于有文字层的单栏、双栏和三栏科研 PDF。解析得到按版面重排的文字，以及能回到原页的区块、词坐标与候选结构。Agent 可据此做全文抽取、定向问答、翻译和字段核验。

## 环境与安装

将提交目录放在 /app/submission，确保 SKILL.md 直接位于目录根。Harbor 将技能安装到 /skills/weekly-skill。其他 Agent 可把该目录注册为本地 Agent Skill，按 SKILL.md 运行。

解析器需要 Python 3.10 或更新版本，以及至少一个本地文字后端。选择顺序为 PyMuPDF、pdftotext、pdfplumber。已有环境可直接使用，也可通过 --backend 指定后端。评分运行中优先复用环境镜像。脚本从 PATH 或当前 Python 环境查找工具，并在本地完成解析。

| 能力 | 本地依赖和来源 |
| --- | --- |
| 文字和词坐标 | [PyMuPDF](https://pymupdf.readthedocs.io/) 1.24+，或带 -bbox-layout 的 [Poppler](https://poppler.freedesktop.org/) pdftotext，或 [pdfplumber](https://github.com/jsvine/pdfplumber) 0.11+ |
| PDF 图像 | Poppler pdftoppm 优先，依次尝试 PyMuPDF 和具备图像后端的 pdfplumber |
| 局部裁剪 | [Pillow](https://pillow.readthedocs.io/)，全页渲染无需 Pillow |
| 扫描页辅助 | [Tesseract](https://tesseract-ocr.github.io/) 5.x 命令、所需语言数据以及上述一个渲染工具。默认 eng，可用 tesseract --list-langs 查看语言 |
| 契约检查 | 标准库检查 case_id 和常见字段描述，可选 [jsonschema](https://python-jsonschema.readthedocs.io/) 4.x 校验显式 JSON Schema |

在自行配置的 Linux 环境可安装系统 poppler-utils，或在既有 Python 虚拟环境中安装一个 Python 文字后端，例如 python3 -m pip install "pdfplumber>=0.11,<0.12"。如果机器已经有文字和渲染后端，可以直接运行。依赖按上游许可证使用，提交包只含自写脚本、说明和样例生成器。本地实测的主路径使用 Python 3.12、pdfplumber 0.11.9 与 pdftoppm 26.07.0。

## 最小调用示例

在技能根目录运行。生成的 PDF 是原创演示样例，内容和编号仅为示例。Windows 可使用已有 Python 的绝对路径替换 python3，且可用斜杠书写路径。

```sh
python3 examples/make_demo.py ./demo-run/demo.pdf
python3 scripts/pdf_evidence.py extract ./demo-run/demo.pdf \
  --out ./demo-run/parsed --case-id demo --ocr off
python3 scripts/pdf_evidence.py find ./demo-run/parsed/index.json "R-27"
python3 scripts/pdf_evidence.py show ./demo-run/parsed/index.json --block P0001-B007 --words
python3 scripts/pdf_evidence.py render ./demo-run/demo.pdf --page 1 \
  --out ./demo-run/page-1.png
```

下面是示例查询输出节选，省略了坐标等诊断字段。区块 ID 以当次 find 返回为准，切换后端或页范围后应重新查找。样例第一页纸面上印着 17，引用中的 page 仍为 1。

```json
[
  {
    "page": 1,
    "id": "P0001-B007",
    "kind": "paragraph",
    "preview": "The sample label is R-27. Record the label with this block ID. This row is a little lower than the left row. The right column ends at this sentence."
  }
]
```

示例问答中，如果实际契约恰好采用以下字段，可将引用写成以下形式。正式案例始终以其原始 output_contract 为准。

```json
{
  "case_id": "demo",
  "status": "success",
  "result": {"label": "R-27"},
  "evidence": [
    {"field": "result.label", "file": "demo.pdf", "page": 1, "printed_page": "17",
     "block_id": "P0001-B007", "quote": "The sample label is R-27."}
  ],
  "uncertainties": [],
  "changes": [
    {"action": "checked source page", "page": 1, "detail": "Verified the extracted label against the rendered PDF."}
  ]
}
```

## 输出与核对

- index.json 记录输入文件名、SHA-256、全书页数、选择的物理页、后端与版本、执行状态、页级标记、候选锚点和跨页续接候选。脚本按页写出解析结果并更新索引。退出码 2 表示调用或读取失败。退出码 0 也可能伴随 partial 或 indeterminate，需读取状态。
- pages/pNNNN.json 记录有顺序的 blocks、候选类型和层级、行区间、词 ID、后端词序和图像区域（支持的后端）。脚注、印刷页码候选、页眉页脚候选均可逐块查证。运行 ID 在当次输出内有效，页图上可按实际版面直接核对。
- reading-order.txt 按物理页列出带 ID 的阅读稿。逐页记录里可查重复页边候选和后端原始词序。空格和分段来自版面推断，逐字引用要核对原页。
- 坐标字段 bbox 采用 [x0, top, x1, bottom]，单位为 PDF 点，原点是当前显示裁切框的左上角。page 从 1 开始。pdf_page_label 来自可读取的 PDF 页标签。印刷页码以页面自身为准。获取局部图用 render 的 --bbox x0 top x1 bottom，可在区块外侧留少量边距。
- 用短语、表题和标题搜索。find 默认匹配空白归并后的文字，运算符和带连字符的术语可用 --regex 或拆成多个词搜索。show --block --words 读精确区块和词坐标，show --page --words 读整页与候选顺序。不同材料的区块 ID 可能相同，引用时同时注明文件。
- 最终结果由 Agent 根据案例要求填写。用 python3 scripts/check_result.py /input/case.json /app/output/result.json 检查契约差异。manual_review 表示原契约仍需手工确认。

## 方法与范围

1. **按区带恢复顺序。** 从词框聚合同行字词，以较大间距切分行片。候选列界先看反复对齐的列首，再核对两侧文字在垂直方向是否同时存在。跨栏文字和可识别的通栏图像切开区带，各区带按栏遍历。基于空白与短题注推断的区带标为待复核。
2. **核对提取完整性。** 重排后验证每个提取词 ID 恰出现一次。这个检查衡量从后端词到块的覆盖，PDF 字体映射或渲染丢字仍需核实。原始词序和几何行片允许复查串栏、局部行序及断词。跨页续接只提供两端锚点。
3. **保守处理特殊元素。** 章节、标题作者区域、脚注、图表题注、表格行和公式编号提供候选。表格跨页合并、复杂单元格归属和二维公式结构需结合页图核验。扫描和图像表可由 OCR 提供第二份证据，仍需目视核对。对极短栏、插入边栏、混合方向文字、复杂浮动图表和特殊字体，先检查位置与原文。校正时保留影响范围和页码。

## 异常及接管

| 现象 | 可核查处理 |
| --- | --- |
| input_missing | 从 task.md 和 case.json 复核原输入位置，记录缺失的材料标识 |
| encrypted_pdf | 记录无法读取的源文件和后端诊断。有授权时改用可访问副本 |
| no_usable_text_backend、extraction_failed 或 tool_timeout | 查看 extraction_attempts，尝试镜像中的另一后端或缩小页范围。也可直接 render 目标页并人工记录 |
| no_native_text 或 sparse_text_over_large_image | 看原页图确认是否扫描、空白或图像型内容。看不到的数据标为无法判断 |
| glyph_mapping_review 或低置信 OCR | 对图确认受影响的词及数值，必要时用 --backend 或另一个工作目录重跑目标页 |
| check_rows_with_wide_internal_gaps | 比较几何行片、原词序与页图，复核栏界或表格布局 |
| 材料之间数值冲突 | 记录双方取值、版本、页码和表或段落，按题目的适用口径处理 |

默认 OCR 只尝试前 5 个需要检查的页，且给每次外部渲染和识别调用单独设定超时。可以从新目录以 --pages、--ocr-limit 和 --ocr-lang 限定重跑。指定 --ocr all 时，完好的原始文字仍保留，OCR 词在逐页记录中另外保存。明确提取范围以及不可读区块，在修改来源、顺序或转写时保留可复核的变更记录。

正式评测使用平台提供的三个固定案例。提交时仅将本目录的技能与资源交给平台。GITHUB_URL.txt 的首行用于填写可匿名访问的本作品链接，第二行可填写相对文件路径。空文件表示本次提交未填公开链接。
