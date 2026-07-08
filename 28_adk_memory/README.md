# 28_adk_memory —— ADK State + Memory + Artifacts（+ Skills 自定义模式）

配套文章：《ADK State + Memory + Artifacts（+ Skills 自定义模式）》

在原有 `demo.py`（连续项目入口）之外，补齐文章文末"包含："承诺的每一件具名产物，均为**独立可运行**脚本。
约定同全系列：`google-adk` 导入 `try/except` 保护，缺依赖打印安装指引并降级到**确定性 mock**，`exit 0`；无 API key 时不联网。

> ⚠️ 边界提醒（文章重点）：**Skill 不是 ADK 原生 API**，是社区/工程师在 ADK 之上自建的"工具+指令+知识"打包模式；`self_built_skill_pattern.py` 演示的是自建模式，其中 `InstructionProvider`（动态指令）才是 ADK 原生能力。State / Memory / Artifacts / Event Sourcing 都是 ADK 原生。

## 安装（跑真实 ADK 时）

```bash
pip install google-adk
export GOOGLE_API_KEY=...   # 或 GEMINI_API_KEY
```

## 产物对照表

| 文章承诺产物 | 文件 | 说明 | 运行 |
|---|---|---|---|
| 自建 Skill 模式完整示例 | `self_built_skill_pattern.py` | Skill dataclass + 注册表 + 渐进加载省 token + InstructionProvider | `python3 28_adk_memory/self_built_skill_pattern.py` |
| State 四作用域完整用法 | `state_scopes_usage.py` | 工业级客服场景，一个工具同时读写 user/app/session/temp | `python3 28_adk_memory/state_scopes_usage.py` |
| Memory Service 自定义实现 | `custom_memory_service.py` | MemoryService 接口 + InMemory + 自定义实现 + `search_memory` | `python3 28_adk_memory/custom_memory_service.py` |
| Artifact 版本化管理 | `artifact_versioning.py` | save/load 多版本 + 文件组织 + 与 state 对照 | `python3 28_adk_memory/artifact_versioning.py` |
| Event Sourcing 审计追溯 | `event_sourcing_audit.py` | Q3 报告 10 步事件流 + 字段级/产物级追溯 | `python3 28_adk_memory/event_sourcing_audit.py` |

## 四个子系统定位

| 子系统 | 解决的问题 | 是否 ADK 原生 |
|---|---|---|
| State | 即时上下文 + user/app 级持久化（4 作用域） | 原生 |
| Memory | 跨会话长期记忆搜索 | 原生（Service 接口） |
| Artifacts | 版本化产物管理 | 原生（Service 接口） |
| Skills | "工具+指令"打包复用 | 非原生，社区自建模式 |

> `demo.py` 仍是连续项目的第 28 章阶段入口，不受本目录新增文件影响。
