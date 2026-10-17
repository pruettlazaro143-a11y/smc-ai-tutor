# SMC AI Tutor · 聪明钱概念 AI 教练

[English](README.en.md) ｜ 中文

把一整套 SMC（Smart Money Concepts，聪明钱概念）知识做成 **AI 能直接执行的教学指令**。上传给任意 AI 助手，它就会变成你的一对一 SMC 教练：按课程带学、随时答疑、出题检验、画 K 线示意图讲解、带你复盘图表。

**看懂流动性猎杀，不再做被扫的那一个。**

![订单区 OB 示意图](diagrams/png/06-订单区OB.png)

## 先说清楚：它是什么，不是什么

这是一个**辅助学习**的工具：帮你把 SMC 的概念串起来，更好地理解一些市场行为背后的逻辑，比如价格为什么总在明显的高低点附近"扫一下"再走，为什么突破之后又迅速收回。

它**替代不了你自己思考的深度和独立判断**。AI 会讲、会画、会出题，但它看不到你没给它的信息，也会出错。真正的能力，来自你自己在图上一遍遍标注、验证、复盘、修正。

> 本项目只做学习用途，不构成任何投资建议。详见文末[免责声明](#免责声明)。

---

## 四种用法

### 1. 任意 AI 助手（推荐，零门槛）

适用于 ChatGPT、Claude、DeepSeek、豆包、Kimi、Gemini 等。

1. 下载 [`prompt/SMC-AI-Tutor.md`](prompt/SMC-AI-Tutor.md)
2. 新开一个对话，把文件作为附件上传（或全文粘贴）
3. 发送 **"开始"**

AI 会先问你三个问题（基础、市场、想怎么学），然后进入对应模式。

### 2. Claude Skill（Claude Code / Claude 应用）

[`skills/smc-learning/`](skills/smc-learning/) 是标准的 Skill 目录，按需读取参考文件，比单文件更省上下文。

- **Claude Code**：把 `skills/smc-learning` 复制到 `~/.claude/skills/`，之后直接问 SMC 相关问题即可触发
- **Claude 应用**：把 `skills/smc-learning` 文件夹压缩成 zip，在技能设置里上传

### 3. 自己读

- [`docs/handbook.md`](docs/handbook.md)：完整学习手册，示意图已嵌入正文
- [`docs/distillation.md`](docs/distillation.md)：高密度认知蒸馏，适合速查，也可以喂给 AI 当知识库
- [`docs/entry-models.md`](docs/entry-models.md)：**进阶概念与入场模型图鉴**，24 张图解，不用 AI 也能直接看

### 4. 加入你自己的 SMC 认知

学的课程、书不同，口径难免有出入。你可以把自己的笔记、蒸馏文件放进来，**同一概念 AI 会以你的口径为准**，第一次用到时标注"这里按你的口径……项目默认说法是……"；你没写的部分照用项目内容。

- **任意 AI**：笔记开头加一行 `<!-- my-smc -->`，和 `SMC-AI-Tutor.md` 一起上传
- **Claude Skill**：放进 [`skills/smc-learning/my-notes/`](skills/smc-learning/my-notes/)，开场自动读取
- **合并成一个文件**：按 [`_template.md`](skills/smc-learning/my-notes/_template.md) 的编号写，运行 `python3 tools/build.py`，生成 `prompt/SMC-AI-Tutor.custom.md`

`my-notes/` 里你自己的文件默认不会提交到 Git，避免误公开。

---

## AI 怎么讲一个概念

每个概念都按同一个节奏：

1. **一句话结论**
2. **生活比喻**
3. **配图**：能渲染图形的环境用 SVG 示意图，只能显示文字的环境自动换成字符图
4. **可检查的规则**
5. **常见误区**
6. **小练习 + 3 道过关题**：答对 2 题再进下一课

四种模式：**系统学习 / 答疑 / 测验 / 看图复盘**。

---

## 课程内容

| 课 | 主题 | 核心问题 |
|---|---|---|
| L0 | SMC 是什么 | 为什么价格会"奇怪地"走 |
| L1 | 市场结构 | 现在是涨、跌还是震荡 |
| L2 | BOS / CHoCH / MSS | 延续和转折怎么区分 |
| L3 | 流动性与清扫 | 止损池在哪，扫了还是真突破 |
| L4 | 诱导 Inducement | 哪个区域是用来被吃掉的 |
| L5 | 位移与 FVG | 什么样的推动才算数 |
| L6 | 订单区 OB 与 POI | OB 的三个硬条件，为什么只取实体 |
| L7 | Premium / Discount | 现在价格贵还是便宜 |
| L8 | 触发与入场 | 扫 → 位移 → CHoCH → 回踩 → 确认 |
| L9 | 多周期与完整流程 | 大周期定方向，小周期找触发，把一切串起来 |
| L10 | 风控、执行与复盘 | 止损、目标、八要素计划、复盘 |
| L11 | 进阶：ICT 补充概念与入场模型 | Breaker、OTE、PO3、SMT，以及 QM / 假突破等 20 个入场模型在 SMC 里对应什么 |

另有 **55 个常见疑问与回答**、20 道综合测验、误区清单、十一步分析清单和复盘模板。

**关于【作者实战经验】**：内容里标有这个标记的部分（如 CISD、拒绝针强弱、心态层误区），是作者在自己交易中遇到具体情况后总结的经验，**不是 SMC 的通用定义**，样本有限。AI 讲到这些内容时会主动说明，请谨慎理解，先在自己的图上验证。

## 示意图

| | |
|---|---|
| ![市场结构](diagrams/png/01-市场结构.png) | ![流动性清扫](diagrams/png/03-流动性清扫.png) |
| ![FVG](diagrams/png/05-FVG三根K线.png) | ![完整入场节奏](diagrams/png/08-完整入场节奏.png) |

基础概念 12 张见 [`diagrams/svg`](diagrams/svg/)，进阶概念与入场模型 24 张见 [`diagrams/models`](diagrams/models/)。

| | |
|---|---|
| ![QM](diagrams/models/png/B01-QM基础形态.png) | ![Breaker](diagrams/models/png/A1-Breaker破坏块.png) |所有示意图都是程序生成的虚构走势，不是真实行情。

---

## 目录结构

```
smc-ai-tutor/
├── SOURCES.md                  # 出处对照
├── prompt/SMC-AI-Tutor.md      # 单文件 AI 指令（任意 AI 可用，自动生成）
├── skills/smc-learning/        # Claude Skill（内容源文件）
│   ├── SKILL.md
│   ├── my-notes/               # 你自己的 SMC 认知（默认不提交）
│   ├── references/             # 01 认知框架 … 05 画图规范
│   └── assets/diagrams/        # SVG 示意图
├── docs/
│   ├── handbook.md             # 学习手册（自动生成）
│   ├── entry-models.md         # 进阶概念与入场模型图鉴（自动生成）
│   └── distillation.md         # 认知蒸馏
├── diagrams/svg | png          # 示意图
└── tools/                      # 生成脚本
```

**内容只改 `skills/smc-learning/references/`**，然后重新生成：

```bash
python3 tools/build.py                          # 生成 prompt/ 和 docs/handbook.md（有 my-notes 时额外生成 custom 版）
python3 tools/gen_diagrams.py                   # 重新生成 SVG 示意图
python3 tools/ob_poster.py                      # 重新生成 OB 一图看懂
python3 tools/gen_models.py                     # 重新生成进阶与入场模型图
python3 tools/render.py diagrams/models/svg diagrams/models/png
python3 tools/render.py diagrams/svg diagrams/png   # SVG 转 PNG（需要 playwright）
```

## 参与贡献

发现定义有误、讲解不清、示意图标错，欢迎提 Issue 或 PR。提交时请说明：

- 改的是哪个概念、原来怎么写、建议怎么改
- 理由（逻辑推导或公开资料来源）
- 请用自己的话写，**不要粘贴付费课程、书籍的原文或截图**

SMC 各流派对部分概念（如 OB 取实体还是整根、CISD 的定义）说法不一。本项目在文中写明了自己的口径，有不同意见欢迎讨论。

## 出处

内容由作者学习、整理和实战复盘而来，文字全部用自己的话重写，示意图全部由脚本生成。主要来源：

- **街哥 SMC 系统教程**（街哥是 X 上知名的 SMC 交易员）
- **Frank Miller《Smart Money Concepts: Unlocking the Path to High Probability Trading》**（推荐购买正版）
- **ICT**（Inner Circle Trader，Michael J. Huddleston）的公开教学概念
- **《ICT 机构价格行为备忘单》**（TRADER_ZHAO 整理）：进阶入场模型的清单
- **作者实战复盘**：标有【作者实战经验】的部分

正文每个小节用 `> 出处：…` 标明来源。完整对照见 [SOURCES.md](SOURCES.md)。

## 免责声明

- 本项目**仅用于学习交流**，不构成任何投资建议，不荐股、不喊单、不带单。
- 交易有风险，**任何方法都不能保证盈利**。请根据自身风险承受能力独立决策，盈亏自负。
- AI 的回答可能出错。请把它当作学习辅助，不要当作交易信号，更不要用它代替自己的判断。
- 标有【作者实战经验】的内容是个人经验总结，不代表普遍规律。

## 许可证

[CC BY-NC-SA 4.0](LICENSE)：

- ✅ 可以免费使用、复制、修改、二次分享
- ✅ 需要署名并注明修改
- ✅ 改编后的作品须以相同许可证发布
- ❌ **禁止任何商业用途**，包括打包出售、做成付费课程或付费群资料
