# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 风格记录变更。

## [0.1.1] - 2026-11-25

### Added
- 新增 [README.md](./README.md)，补充项目介绍、目录结构、安装与权限脚本用法以及新版 Antigravity 兼容性说明。
- 新增 [CHANGELOG.md](./CHANGELOG.md)，记录基线功能与 Antigravity 版本兼容性审计结论。
- 新增 [AGENTS.md](./AGENTS.md)，定义在本仓库中开发、版本发布（commit 前更新版本号与 `CHANGELOG.md`）及验证的 Agent 约定。
- 新增 [.gitignore](./.gitignore)，忽略 Python 缓存、`.DS_Store` 与 `.bak` 备份文件。

### Fixed
- 修复 [scripts/install.sh](./scripts/install.sh) 生成的 `~/.gemini/config/rules/antigravity-sandbox-git-rules.md` 缺少 YAML frontmatter（`trigger: always_on`）导致被 Antigravity 静默忽略的问题。
- 修复 [scripts/install.sh](./scripts/install.sh) 直接调用 `python3` 在 macOS 沙箱环境命中 `/usr/bin/python3` (`xcrun` shim) 失败的风险，改为优先探测 `/opt/homebrew/bin/python3` 与 CLT `python3`。
- 修复 [scripts/compact-reminder.py](./scripts/compact-reminder.py) 中 `invocationNum` 过滤条件误写为 `!= 1` 的问题，改为与 `hooks.md` 一致的 0-indexed 判断（`!= 0`），确保首轮模型调用即可触发检查。

### Changed
- 更新 [SKILL.md](./SKILL.md) 与 [references/config-and-permissions.md](./references/config-and-permissions.md)：补充 `trigger: always_on` frontmatter 说明、`CLI v1.5.15+` 的 `AGY_CLI_AUTO_COMPACT_OVERRIDE`、以及最新 `permissions.md` 对 `$VAR` 参数与透明包装器前缀匹配规则的准确界定。

### Compatibility Audit (2026-11-25)
针对 **Antigravity App `v2.35.1`**、**Antigravity CLI `v1.5.16`**、**Antigravity IDE `v2.8.0`** 及官方文档（`hooks.md`、`rules.md`、`skills.md`、`permissions.md`、`sandbox.md`、`customization-discovery.md`）的核查结果：

- **Confirmed Compatible**
  - macOS 终端沙箱在 `v2.35.1` 中调用 `/usr/bin/git` 仍因读取 `/var/db/xcode_select_link` 失败，CLT `git` 路径绕过方案仍适用。
  - `hooks.json` 的 `PreInvocation` 定义格式、`injectSteps` 输出结构及 `lastUserInput` 字段与最新 `hooks.md` 一致。
  - `v2.35.1` 会话 `transcript.jsonl` 中 `PLANNER_RESPONSE` 仍保留 `input_tokens`、`cache_read_tokens`、`step_index` 字段，`compact-reminder.py` 解析逻辑兼容。
  - Skill 路径 `~/.gemini/config/skills/agy_speed_up` 仍是 Antigravity App 与 CLI 共同扫描的跨端个人 Skill 目录。
- **Behavioral Overlap & Platform Notes**
  - `agy` CLI `v1.5.15+` 已内置 `AGY_CLI_AUTO_COMPACT_OVERRIDE` 与 `/context` 自动压缩阈值展示，与本项目的 CLI 侧 `/compact` 提醒存在功能互补（App 端仍无替代）。
  - App `v2.35.0+` 强化了敏感配置目录与内部会话连接文件的访问保护，进一步确认 `configure-project-permissions.py` 应在外部终端运行。

## [0.1.0] - 2026-11-24

### Added
- 新增 [SKILL.md](./SKILL.md)：定义 `agy-speed-up` Skill，汇总沙箱加速、长上下文压缩提醒、JSON 权限管理与 `transcript.jsonl` 延迟诊断流程。
- 新增 [scripts/install.sh](./scripts/install.sh)：支持 `--global-rule`、`--project-hook <repo_dir>`、`--global-hook`、`--link-skill` 与 `--all` 安装选项。
- 新增 [scripts/compact-reminder.sh](./scripts/compact-reminder.sh) 与 [scripts/compact-reminder.py](./scripts/compact-reminder.py)：实现基于 `PreInvocation` 的低开销 `/compact` Token 阈值提醒 Hook，支持 `AGY_COMPACT_WARN_TOKENS`、`AGY_COMPACT_REPEAT_STEP_TOKENS`、`AGY_COMPACT_REMIND_EVERY_TURN`。
- 新增 [scripts/configure-project-permissions.py](./scripts/configure-project-permissions.py)：支持按项目目录匹配 `~/.gemini/config/projects/<id>.json`，查看配置、应用 `auto` / `sandbox-auto` 预设或复制 `permissionGrants`（默认 dry-run，`--apply` 写入前创建 `.json.bak` 备份）。
- 新增 [references/config-and-permissions.md](./references/config-and-permissions.md)：整理 Antigravity 全局/CLI/项目配置路径、v2 Schema、沙箱挂载规则与命令自动审批注意事项。
