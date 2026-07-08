# 13_chunking — Chunking 决定 RAG 上限：6 种切块策略实战（配套产物）

第 13 篇《RAG 进阶 3》文末「包含：」承诺的产物清单与文件对照。RAG 的天花板不在向量库、
不在 Embedding，在切块——再先进的检索器，输入材料被切散、丢上下文，召回的东西就永远
是错的、散的。

> 所有脚本**离线可运行**、纯 stdlib 优先。离线 embedding = 词频向量 + 余弦；
> 有 `OPENAI_API_KEY` + `openai` 时可切真 embedding。导入不发起网络请求。

## 文章「包含：」→ 文件对照表

| 文章承诺的产物 | 文件 | 说明 |
|---|---|---|
| 6 种切块策略的可运行实现 | `chunking_strategies.py` | fixed_size / recursive_character / sentence / structure_heading / semantic / parent_child，统一接口 + 对照表 |
| 语义切块阈值调优脚本 | `semantic_chunking_tuning.py` | 相邻句相似度表 + 阈值扫描（chunk 数/平均长度/切点数），找语义跳变拐点 |
| 父子文档检索完整 demo | `parent_child_retrieval.py` | `ParentChildStore`：子 chunk 精准检索 → 返回父 chunk 完整上下文 |
| Python AST 切块器 | `python_ast_chunker.py` | `ast` 按函数/类语法单元切，绝不切断函数体，带 name/lineno/docstring；支持传入 .py 文件 |
| Markdown 标题路径切块器 | `markdown_header_chunker.py` | 按 H1/H2/H3 切并保留父标题路径消歧；支持传入 .md 文件 |
| 完整 metadata schema 设计 | `metadata_schema.py` | `ChunkMetadata` dataclass（溯源/结构/治理/标识四组字段）+ 校验器 |
| 公共离线工具 | `_common.py` | 示例手册文本、离线相似度、打印工具 |

## 运行

```bash
python3 13_chunking/chunking_strategies.py
python3 13_chunking/semantic_chunking_tuning.py
python3 13_chunking/parent_child_retrieval.py
python3 13_chunking/python_ast_chunker.py [file.py]
python3 13_chunking/markdown_header_chunker.py [file.md]
python3 13_chunking/metadata_schema.py
```

> 连续项目统一入口（`demo.py` / `chapter_runner 13`）见同目录 `README.md`。
