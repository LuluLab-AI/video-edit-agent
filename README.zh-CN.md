# AI 自动化剪辑

## 概述

本 Skill 将用户提供的真人实拍素材剪成带口播的竖屏视频变体，适合拥有素材使用权的创作者与商家。Agent Skills 根目录是本仓库的 `video-edit-agent/`，其中包含 `SKILL.md`。

## 主要能力

- 使用原录音，或提供文案和可选音色。
- 按口播语义选镜头，添加字幕和可选的固定音量音乐，制作多个版本，并在本地渲染和质检。
- 通过随包 LuluLab Node.js CLI 获取服务端剪辑策略。

## 环境要求

需要能操作文件和 Agent Skills 的智能体（如 Codex 或 Claude Code）、Python 3、FFmpeg/FFprobe、Node.js 20+，以及 macOS 或 Windows。文案口播使用操作系统语音能力。远端策略阶段需要网络和 LuluLab API Key。其他智能体需要等效的文件型 Skill 机制。

## 安装

可向智能体发送：

> 请将这个 LuluLab Skill 安装到我当前使用的 AI 智能体环境：https://github.com/LuluLab-AI/video-edit-agent 。请遵循项目的官方安装说明。

检查仓库后，把完整 `video-edit-agent/` 文件夹复制到当前智能体的用户 Skill 目录，名称保持 `video-edit-agent`。各智能体目录不同，应按其当前文档确认。保留 `SKILL.md`、`scripts/`、`references/` 和 `input/config.json`。不要把源码命名空间 `@indiv-lululab` 嵌套到 Skill 根目录。已有同名 Skill 时先比较版本，替换前征求用户确认；不碰其他 Skill。在根目录运行 macOS 的 `python3 scripts/workbuddy_preflight.py` 或 Windows 的 `py -3 scripts\workbuddy_preflight.py`，然后重新加载并确认可识别。

本次将旧名称 `ai-video-editor` 改为 `video-edit-agent`。如果旧名称已安装，先征求用户同意，再停用或移除旧版本，避免同一工作流出现两个入口。

## 快速开始

- “用 $video-edit-agent 把我提供的真人产品演示素材剪成两个竖屏版本，使用原录音口播。”
- “把我提供的素材剪成 25 秒 UGC 视频，用 `input/voiceover_script.txt` 作英文口播。”

素材放入 `input/videos/`，在 `input/config.json` 中选择 `audio` 或 `script`。完整流程见 [SKILL.md](SKILL.md)。

## 配置

用 `node scripts/lululab_cli.mjs --help` 离线检查客户端。到远端策略阶段前在本机设置 `LULULAB_API_KEY`。Skill 届时通过 `scripts/validate_lululab_api_key.py` 和 CLI 只读 `user --credits` 验证。策略使用 `task submit --workflow-id VideoEditingPolicyV1 --input-file <JSON 文件>` 和 `task fetch --id <任务 ID>`。无需 npm 或 `npx` 安装。不要把 Key 写入仓库、日志或命令参数。详见 [CLI 配置](references/lululab-cli-setup.md)。

## 支持语言

中英文交互遵循[现有语言规则](references/interaction-language.md)。原录音和字幕保留实际语言；明确的成片语言要求用于生成内容。

## 常见问题

| 问题 | 检查方法 |
| --- | --- |
| 无法识别 Skill | 检查根目录和 `SKILL.md`，重新加载智能体的 Skill 列表。 |
| 找不到 CLI | 确认 Node.js 20+ 和 `scripts/lululab_cli.mjs`，运行 `--help`。 |
| 缺少 API Key | 到策略阶段时在本机设置 `LULULAB_API_KEY`。 |
| 网络请求失败 | 检查连接；重试前先恢复已保存的任务 ID。 |
| 模型或策略调用失败 | 查看任务状态，确认状态前不重复付费请求。 |
| 缺少依赖 | 执行平台预检，安装报告指出的组件。 |

## 支持

网站：https://lululab.ai  
邮箱：contact@lululab.ai
