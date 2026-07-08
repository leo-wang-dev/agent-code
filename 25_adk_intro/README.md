# 25_adk_intro —— Google ADK 入门：五件套心智模型

配套文章：《Google ADK 入门 —— Agent / Tool / Runner / Session / Events 五件套》

本目录在原有 `demo.py`（连续项目入口）之外，补齐文章文末"包含："承诺的每一件具名产物，
均为**独立可运行**脚本。所有脚本遵循同一约定：

- `google-adk` 的导入全部 `try/except` 保护，缺依赖时打印安装指引，继续用**确定性 mock**演示同一套 API 形态，`exit 0`；
- 模型调用在无 `GOOGLE_API_KEY` / `GEMINI_API_KEY` 时走确定性 mock，不联网；
- 以文章正文展示的 ADK API 为准，真实写法在每个脚本头部注释里给出。

## 安装（跑真实 ADK 时）

```bash
pip install google-adk
export GOOGLE_API_KEY=...   # 或 GEMINI_API_KEY
```

未安装也能跑：脚本会自动降级到 mock 演示。

## 产物对照表

| 文章承诺产物 | 文件 | 说明 | 运行 |
|---|---|---|---|
| 5 件套最小示例 | `five_piece_minimal.py` | Agent/Tool/Runner/Session/Events 组装 + 事件流输出 | `python3 25_adk_intro/five_piece_minimal.py` |
| ADK 标准项目骨架模板 | `project_skeleton_template.py` | 打印/生成文章推荐的四层目录结构脚手架 | `python3 25_adk_intro/project_skeleton_template.py [目标目录]` |
| 4 作用域 State 完整 demo | `state_four_scopes.py` | `session`/`user:`/`app:`/`temp:` 前缀分发与跨 session 存活验证 | `python3 25_adk_intro/state_four_scopes.py` |
| Event 事件流捕获脚本 | `event_capture.py` | 捕获不可变 Event 流，回放重建 state / artifact 版本 | `python3 25_adk_intro/event_capture.py` |
| Service 注入对比 | `service_injection_compare.py` | InMemory(开发) vs Database/File(生产) 零代码切换 | `python3 25_adk_intro/service_injection_compare.py` |

> `demo.py` 仍是连续项目的第 25 章阶段入口，不受本目录新增文件影响。
