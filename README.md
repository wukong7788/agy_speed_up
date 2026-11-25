# AGY Speed Up

用于诊断和加速 **Google Antigravity**（Antigravity App / IDE / `agy` CLI）工作流的 Skill 与自动化工具集。核心目标是消除不必要的 `BypassSandbox` 人工审批等待、在长上下文导致思考变慢前提醒执行 `/compact`，以及通过 JSON 配置文件跨项目/跨机器复用权限与沙箱策略。

## 目录结构

```text
agy_speed_up/
├── SKILL.md                              # Antigravity Skill 定义与使用手册
├── AGENTS.md                             # 本仓库的 Agent 协作规范与验证约定
├── README.md                             # 项目说明文档（本文件）
├── CHANGELOG.md                          # 变更记录与 Antigravity 版本兼容性审计
├── references/
│   └── config-and-permissions.md         # Antigravity 配置路径、v2 JSON Schema 与审批规则参考
└── scripts/
    ├── install.sh                        # 一键安装全局规则、链接 Skill、部署 /compact Hook
    ├── compact-reminder.sh               # Hook 入口包装脚本（自动探测 python3 路径）
    ├── compact-reminder.py               # PreInvocation Hook：基于 transcript token 阈值提示 /compact
    └── configure-project-permissions.py  # 安全查看/修改项目权限 JSON（默认 dry-run + 自动备份）
```

## 核心功能

### 1. 消除 macOS 本地 `git` 的 `BypassSandbox` 等待（50s+）
- **根因**：在 macOS 上，`/usr/bin/git` 是 `xcrun` shim，执行时会读取 `/var/db/xcode_select_link`。在 Antigravity 默认终端沙箱（`sandbox-exec`）中该读取会触发 `Operation not permitted`，导致 Agent 退化为申请 `BypassSandbox: true` 并等待人工确认。
- **方案**：在本地非网络 `git` 命令（`status`、`diff`、`log`、`show`、`branch`、`rev-parse`、`add`、`commit`、`restore`、`switch`）中直接调用 `/Library/Developer/CommandLineTools/usr/bin/git`，仅在网络操作（`push`、`fetch`、`pull`、`clone`、`ls-remote`）或 CLT 不可用时使用 `BypassSandbox: true`。

### 2. Token 阈值 `/compact` 提醒 Hook（零模型开销）
- **原理**：通过 Antigravity `PreInvocation` Hook 读取当前会话 `transcriptPath` 末尾最新的 `PLANNER_RESPONSE`，计算 `input_tokens + cache_read_tokens`。
- **零上下文污染**：输出 `systemMessage: ""` 配合 `metadata.user_markdown`，仅在 UI 展示内联提示横幅，不消耗额外模型调用，也不向提示词注入冗余文本；按步长分桶去重，避免每轮重复刷屏。
- **环境变量配置**：
  - `AGY_COMPACT_WARN_TOKENS`：首次提醒阈值，默认 `250000`（最低限制 `50000`）
  - `AGY_COMPACT_REPEAT_STEP_TOKENS`：升级提醒步长，默认 `100000`（最低限制 `25000`，即 250k、350k、450k…）
  - `AGY_COMPACT_REMIND_EVERY_TURN`：设为 `1` 时在超过阈值后每轮都提醒（默认 `0`）

### 3. 基于 JSON 的项目权限与预设管理
- Antigravity 将全局和项目级权限持久化于：
  - `~/.gemini/config/config.json`（全局 App 配置，受系统保护，需用户自行编辑）
  - `~/.gemini/antigravity-cli/settings.json`（`agy` CLI 配置）
  - `~/.gemini/config/projects/<project-id>.json`（单项目配置与 `permissionGrants`）
- `scripts/configure-project-permissions.py` 支持按仓库路径自动匹配项目 JSON，应用预设（`auto` / `sandbox-auto`）、修改单项 `settings`，或从已验证的样本项目复制 v2 `permissionGrants`（默认 dry-run，传入 `--apply` 才会写入并先生成 `.json.bak` 备份）。

## 快速安装与使用

### 安装 Skill、全局规则与 Hook

```bash
# 1. 安装 macOS CLT git 全局规则 + 软链接本 Skill 到 ~/.gemini/config/skills/agy_speed_up
bash ./scripts/install.sh --global-rule --link-skill

# 2. 为指定项目安装 /compact 提醒 Hook（写入 <repo>/.agents/hooks.json 与 .agents/hooks/）
bash ./scripts/install.sh --project-hook /path/to/repo

# 可选：全局安装 /compact 提醒 Hook（写入 ~/.gemini/config/hooks.json）
bash ./scripts/install.sh --global-hook

# 或者一次性执行全局规则 + 链接 Skill + 全局 Hook
bash ./scripts/install.sh --all
```

### 检查或同步项目权限 JSON（需在外部终端运行）

> [!NOTE]
> 受 Antigravity 系统保护机制限制，沙箱内 Agent 无法直接读写 `~/.gemini/config/`；请在宿主机外部终端中运行以下命令。

```bash
# 查看当前仓库对应的项目配置文件
python3 -B ./scripts/configure-project-permissions.py --project-dir /path/to/repo --show

# 预览将项目切换为 auto 预设并允许非工作区文件访问（dry-run）
python3 -B ./scripts/configure-project-permissions.py \
  --project-dir /path/to/repo \
  --preset auto \
  --set fileAccessPolicy=AGENT_SETTING_POLICY_ALLOW

# 从已验证的项目配置文件克隆 permissionGrants 并写入（自动生成 .json.bak）
python3 -B ./scripts/configure-project-permissions.py \
  --project-dir /path/to/repo \
  --copy-grants-from ~/.gemini/config/projects/<golden-id>.json \
  --apply
```

## 与 Antigravity 新版兼容性说明

已针对 **Antigravity App `v2.35.1`**、**Antigravity CLI `v1.5.16`** 与 **Antigravity IDE `v2.8.0`** 的官方更新进行核对（详见 [CHANGELOG.md](./CHANGELOG.md)）：

- **macOS `git` 沙箱问题依然存在**：`v2.35.1` 沙箱中调用 `/usr/bin/git` 仍会触发 `/var/db/xcode_select_link` 的 `Operation not permitted`，CLT `git` 规则仍然有效且必要。`scripts/install.sh --global-rule` 已为生成的 `~/.gemini/config/rules/antigravity-sandbox-git-rules.md` 补全必需的 `trigger: always_on` YAML frontmatter。
- **`hooks.json` 与 `transcript.jsonl` Schema 兼容**：`PreInvocation`（`invocationNum == 0` 首轮触发）、`injectSteps.systemMessage.metadata.user_markdown`、`lastUserInput` 以及 `PLANNER_RESPONSE` 的 `input_tokens` / `cache_read_tokens` / `step_index` 字段均与新版一致。
- **使用与平台差异提示**：
  1. **重装已部署的全局规则**：若之前运行过旧版 `install.sh --global-rule`，请重新运行一次以更新 `~/.gemini/config/rules/antigravity-sandbox-git-rules.md` 的 YAML frontmatter，否则旧的无 frontmatter 版本会被 Antigravity 静默忽略。
  2. **CLI 原生自动压缩阈值**：`agy` CLI `v1.5.15+` 已在 `/context` 中内置自动压缩阈值显示，并通过 `AGY_CLI_AUTO_COMPACT_OVERRIDE`（支持 token 数、`K`/`M` 或百分比）支持全局模型自定义压缩阈值；本仓库的 `compact-reminder` 更适合在 Antigravity App 中以及在 CLI 达到更高上限前提前于 `250k` 给出手动 `/compact` 提示。
  3. **配置目录保护强化**：App `v2.35.0` 进一步限制了沙箱及文件工具对内部会话与敏感配置目录的访问，验证了 `configure-project-permissions.py` 必须在外部终端执行的设计。
