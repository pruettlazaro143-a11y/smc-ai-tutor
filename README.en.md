# SMC AI Tutor

English ｜ [中文](README.md)

A complete Smart Money Concepts (SMC) curriculum packaged as **instructions any AI assistant can run**. Upload one file and your AI becomes a one-on-one SMC tutor: it teaches lesson by lesson, answers questions, quizzes you, draws candlestick diagrams, and walks you through chart reviews.

**Learn to read liquidity hunts — and stop being the liquidity.**

![Order block diagram](diagrams/png/06-订单区OB.png)

> For education only. Not investment advice. See the [disclaimer](#disclaimer).

> **Language note:** the source material is written in Chinese. The AI tutor can still teach in English. Just say "Please teach in English" after you send "开始" (start).

---

## Three ways to use it

### 1. Any AI assistant (recommended)

Works with ChatGPT, Claude, Gemini, DeepSeek, Kimi, Doubao and others.

1. Download [`prompt/SMC-AI-Tutor.md`](prompt/SMC-AI-Tutor.md)
2. Start a new chat and attach the file (or paste it in full)
3. Send **"开始"** (or "start, please teach in English")

The tutor first asks about your level, your market, and how you want to learn, then switches to the matching mode.

### 2. Claude Skill (Claude Code / Claude apps)

[`skills/smc-learning/`](skills/smc-learning/) is a standard Skill folder. It loads reference files on demand, so it uses less context than the single-file prompt.

- **Claude Code**: copy `skills/smc-learning` into `~/.claude/skills/`, then ask any SMC question
- **Claude apps**: zip the `skills/smc-learning` folder and upload it in your Skills settings

### 3. Read it yourself

- [`docs/handbook.md`](docs/handbook.md): the full handbook, with diagrams embedded
- [`docs/distillation.md`](docs/distillation.md): a dense summary for quick reference, or to give an AI as a knowledge base

---

## How the tutor teaches a concept

Every concept follows the same rhythm:

1. **One-line takeaway**
2. **Everyday analogy**
3. **Diagram**: SVG where the chat can render graphics, ASCII charts where it can't
4. **Checkable rules**
5. **Common mistakes**
6. **Exercise and 3 checkpoint questions**: get 2 right to move on

Four modes: **guided course / Q&A / quiz / chart review**.

## Curriculum

| Lesson | Topic |
|---|---|
| L0 | What SMC is and why price moves "strangely" |
| L1 | Market structure (HH / HL / LH / LL) |
| L2 | BOS / CHoCH / MSS |
| L3 | Liquidity and sweeps |
| L4 | Inducement |
| L5 | Displacement and fair value gaps (FVG) |
| L6 | Order blocks (OB) and POI. Body-only zones |
| L7 | Premium / discount |
| L8 | Triggers and entry sequence |
| L9 | Multi-timeframe analysis and the full workflow |
| L10 | Risk, execution and review (8-point trade plan) |

Plus **49 frequently asked questions**, a 15-question final quiz, a list of common mistakes, an 11-step analysis checklist and a review template.

All diagrams in [`diagrams/`](diagrams/) are generated from synthetic price data, not real market charts.

## Editing and rebuilding

Edit content **only** in `skills/smc-learning/references/`, then rebuild:

```bash
python3 tools/build.py                              # rebuilds prompt/ and docs/handbook.md
python3 tools/gen_diagrams.py                       # regenerates SVG diagrams
python3 tools/ob_poster.py                          # regenerates the OB one-pager
python3 tools/render.py diagrams/svg diagrams/png   # SVG → PNG (requires playwright)
```

## Contributing

Issues and PRs are welcome for wrong definitions, unclear explanations or mislabeled diagrams. Please explain your reasoning, and write in your own words. **Do not paste text or screenshots from paid courses or books.**

SMC schools disagree on some details, for example whether an OB covers the whole candle or only the body, or how CISD is defined. This project states its own conventions explicitly. Discussion is welcome.

## Disclaimer

- For learning only. This project gives no investment advice, trade signals or managed trading.
- Trading carries risk, and **no method guarantees profit**. Make your own decisions within your own risk tolerance.
- AI answers can be wrong. Treat the tutor as a study aid, not a signal service.

## License

[CC BY-NC-SA 4.0](LICENSE). You may use, copy, adapt and share this project for free with attribution, and adaptations must use the same license. **Commercial use is not permitted**, including selling it or bundling it into paid courses or paid groups.
