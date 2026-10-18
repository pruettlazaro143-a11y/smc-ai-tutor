"""从 skills/smc-learning/references/ 和 tools/tutor_core.md 生成：
  skills/smc-learning/SKILL.md —— Claude Skill 的教练指令
  prompt/SMC-AI-Tutor.md       —— 单文件通用 AI 指令（任意 AI 可用）
  docs/handbook.md             —— 给人读的学习手册（嵌入示意图）
  docs/entry-models.md         —— 进阶概念与入场模型图鉴
字符图库 07 由 tools/gen_ascii.py 生成；08 里的标注代码自动同步自 tools/annotate.py。
在仓库根目录运行：python3 tools/build.py
"""
import re

R = 'skills/smc-learning/references/'


def read(path):
    return open(path, encoding='utf-8').read()


# ---------- 0. 同步代码：08 里嵌入的标注代码 = tools/annotate.py ----------
p08 = R + '08-截图标注规范.md'
t08 = read(p08)
code = read('tools/annotate.py').rstrip()
t08 = re.sub(r'(## 四、[^\n]*\n.*?```python\n).*?(\n```)', lambda m: m.group(1) + code + m.group(2), t08, count=1, flags=re.S)
open(p08, 'w', encoding='utf-8').write(t08)

# ---------- 1. 教练指令：SKILL.md 与通用单文件共用 tools/tutor_core.md ----------
TITLES = {}
for f in ['01-认知框架.md', '02-常见疑问与回答.md', '03-学习路径与练习.md', '04-误区与清单.md',
          '05-画图规范.md', '06-进阶概念与入场模型.md', '07-字符图库.md', '08-截图标注规范.md']:
    TITLES[f[:2]] = (f, read(R + f).split('\n', 1)[0].lstrip('# ').strip())

core = read('tools/tutor_core.md')
SKILL_TOK = {
    'SRC': '`references/` 下的文件',
    'NAV': '\n'.join(['| 需要做什么 | 读哪个文件 |', '|---|---|',
                      '| 讲概念、定义、规则 | `references/01-认知框架.md`（知识主干，以此为准） |',
                      '| 回答学员提问 | `references/02-常见疑问与回答.md`（先找原题，找不到再按 01 推理） |',
                      '| 系统带课、出练习和测验 | `references/03-学习路径与练习.md` |',
                      '| 讲误区、给清单、做复盘 | `references/04-误区与清单.md` |',
                      '| 选展示形式、画图、标注前核对 | `references/05-画图规范.md` + `assets/diagrams/*.svg` |',
                      '| 进阶：ICT 补充概念、QM / 供需入场模型（L11） | `references/06-进阶概念与入场模型.md` + `assets/models/*.svg` |',
                      '| 只能显示文字时的图 | `references/07-字符图库.md`（原样使用，不要改字符） |',
                      '| 学员发截图、要你标注 | `references/08-截图标注规范.md` |',
                      '| 学员自己的认知 | `my-notes/*.md`（README 和 _template 除外） |',
                      '', '只读当前需要的文件，不要一次全读。']),
    'LOAD_NOTES': '先查看本 Skill 目录下的 `my-notes/` 文件夹：除了 `README.md` 和 `_template.md`，其他 `.md` 文件都是学员的认知，读取它们。',
    'NOTES_WHERE': '来源有三种：本 Skill 的 `my-notes/` 文件夹里的 `.md` 文件（README 和 _template 除外）；学员在对话里上传或粘贴的笔记；学员在对话中让你记下的内容。',
    'SAVE_HOW': '如果你能写文件（例如在 Claude Code 里），征得学员同意后，把记录写入本 Skill 的 `my-notes/my-smc.md`（已存在就追加，不覆盖），下次开场会自动读取。不能写文件时，用"导出我的认知"把 `my-smc.md` 给学员，请他放进 `my-notes/` 文件夹。',
}
for k, (f, title) in TITLES.items():
    SKILL_TOK['F' + k] = f'`references/{f}`'
UNI_TOK = {
    'SRC': '本文件后面的教材部分（01–08）',
    'NAV': '本文件后面依次是：' + '；'.join(f'「{t}」' for _, t in TITLES.values()) + '。按需要查对应部分，不要复述。',
    'LOAD_NOTES': '检查本文件里有没有"【用户口径】"块（用工具合并过的版本才有），以及对话里有没有学员另外上传的笔记（开头带 `<!-- my-smc -->`，或学员说明这是自己的认知），有就读取。',
    'NOTES_WHERE': '来源有三种：本文件里的"【用户口径】"块（用工具合并过的版本才有）；学员在对话里上传或粘贴的笔记（开头带 `<!-- my-smc -->`，或学员说明这是自己的认知）；学员在对话中让你记下的内容。',
    'SAVE_HOW': '普通对话关掉后就不记得了。告诉学员三种保存办法：① 说"导出我的认知"，把 `my-smc.md` 存下来，下次和本文件一起上传；② 如果所用的 AI 有"记忆"或"项目 / 知识库"功能，把 `my-smc.md` 放进去；③ 用 GitHub 仓库里的 `tools/build.py` 把它合并进指令，以后只上传一个文件。',
}
for k, (f, title) in TITLES.items():
    UNI_TOK['F' + k] = f'「{title}」'


def fill(text, tok):
    out = re.sub(r'\{\{(\w+)\}\}', lambda m: tok[m.group(1)], text)
    assert '{{' not in out, 'unfilled token'
    return out


skill_md = read('skills/smc-learning/SKILL.md')
fm = skill_md[:skill_md.index('---', 3) + 3]
open('skills/smc-learning/SKILL.md', 'w', encoding='utf-8').write(
    fm + '\n\n<!-- 本文件由 tools/build.py 根据 tools/tutor_core.md 生成，修改请改源文件 -->\n\n# SMC 认知学习 · 常见疑问与回答\n\n' + fill(core, SKILL_TOK))

# ---------- 2. 通用单文件 AI 指令 ----------
ascii_map = {'01': '1', '02': '2', '03': '3', '04': '4', '05': '5', '06': '6', '07': '10', '08': '7', '09': '8', '10': '9'}


def to_ascii_ref(t):
    def rep(mo):
        ids = re.findall(r'(\d\d)-', mo.group(0))
        refs = sorted({ascii_map[i] for i in ids if i in ascii_map}, key=int)
        return f'（字符图库第 {"、".join(refs)} 张）' if refs else ''
    return re.sub(r'（配图：[^）]*）', rep, t)


head = read('tools/universal_header.md')
parts = [head + '\n' + fill(core, UNI_TOK).replace('\n## ', '\n### ') +
         '\n\n**读完本文件后，不要复述内容，直接按"开场"打招呼并提出五个问题。**']
for f in ['01-认知框架.md', '02-常见疑问与回答.md', '03-学习路径与练习.md', '04-误区与清单.md',
          '05-画图规范.md', '06-进阶概念与入场模型.md', '07-字符图库.md', '08-截图标注规范.md']:
    t = to_ascii_ref(read(R + f))
    if f.startswith('05'):
        t = t.replace('能读取文件时，优先用 `assets/diagrams/`（基础概念）和 `assets/models/`（进阶与入场模型）里的 SVG，原样输出或嵌进最简 HTML 页面。索引见第四节。',
                      '（这一项只在 Claude Skill 环境里可用：Skill 文件夹里带有现成的 SVG 示意图。单文件版本里没有这些文件，请改用 2.2 现画。）')
    parts.append(t)
u = '\n\n---\n\n'.join(parts)
u = u.replace('| 课 | 主题 | 核心问题 | 配图 |', '| 课 | 主题 | 核心问题 | 字符图库 |')
for a, b in [('| 00 |', '| — |'), ('| 01 |', '| 1 |'), ('| 02 |', '| 2 |'), ('| 03、09 |', '| 3、8 |'),
             ('| 04 |', '| 4 |'), ('| 05 |', '| 5 |'), ('| 06 |', '| 6 |'), ('| 07 |', '| 10 |'),
             ('| 08、10 |', '| 7、9 |'), ('| 00、08 |', '| 7 |'), ('| models/ |', '| 06 各节 |')]:
    u = u.replace(a, b)
open('prompt/SMC-AI-Tutor.md', 'w', encoding='utf-8').write(u)

# 精简版：去掉进阶模型的字符图和标注代码，给上下文较短、读不全大文件的 AI 用
lite = u
i = lite.index('## A1 破坏块 Breaker')
j = lite.index('# 08 · 看图复盘与截图标注')
lite = lite[:i] + '（精简版省略了进阶入场模型的字符图，需要时请用完整版 SMC-AI-Tutor.md。）\n\n---\n\n' + lite[j:]
lite = re.sub(r'(## 四、直接画在原图上的代码[^\n]*\n).*?(?=\Z)', lambda m: m.group(1) + '\n精简版不含标注代码。需要直接在截图上画标注时，请改用完整版 SMC-AI-Tutor.md，或输出第三节格式的 JSON，让学员用仓库里的 annotator/index.html（标注器）打开。\n', lite, count=1, flags=re.S)
lite = lite.replace('# SMC AI 教程指令 · SMC AI Tutor', '# SMC AI 教程指令 · SMC AI Tutor（精简版 Lite）', 1)
open('prompt/SMC-AI-Tutor-lite.md', 'w', encoding='utf-8').write(lite)


# ---------- 1b. 合并用户自定义认知（有 my-notes 时） ----------
import glob, os

ANCHORS = {  # 编号 → 01-认知框架 中对应的标题开头
    '结构': '## 2. 市场结构', 'BOS': '### 2.3 ', 'CHOCH': '### 2.3 ', 'MSS': '### 2.3 ',
    '流动性': '### 3.1 ', '诱导': '### 3.2 ', 'IDM': '### 3.2 ', '清扫': '### 3.4 ',
    'FVG': '## 4. ', 'CISD': '### 4.4 ', 'OB': '## 5. ', 'POI': '## 5. ',
    '区间': '## 6. ', '触发': '## 7. ', '拒绝针': '### 7.3 ', '多周期': '## 8. ',
    '流程': '## 9. ', '止损目标': '## 10. ', '心态': '## 11. ',
    'ICT': '## A. ICT', '进阶': '## A. ICT', 'QM': '## B. QM', '入场模型': '## B. QM',
}
notes = [f for f in sorted(glob.glob('skills/smc-learning/my-notes/*.md'))
         if os.path.basename(f) not in ('README.md', '_template.md')]
if notes:
    blocks = []  # (编号, 来源文件, 内容)
    for f in notes:
        txt = re.sub(r'<!--.*?-->', '', read(f), flags=re.S)
        parts_ = re.split(r'^## \[([^\]]+)\][^\n]*\n', txt, flags=re.M)
        if len(parts_) == 1:  # 没按模板写：整份作为"其他"
            blocks.append(('其他', f, txt.strip()))
        for i in range(1, len(parts_), 2):
            blocks.append((parts_[i].strip(), f, parts_[i + 1].strip()))

    def quote(id_, src, body):
        lines = [f'> **【用户口径 · {id_}】**（来自 `{os.path.basename(src)}`。优先使用；第一次用到时注明与项目默认口径的差异）', '>']
        lines += ['> ' + ln if ln else '>' for ln in body.split('\n')]
        return '\n'.join(lines) + '\n\n'

    c = u
    others = []
    for id_, src, body in blocks:
        if not body:
            continue
        anchor = ANCHORS.get(id_.upper(), ANCHORS.get(id_))
        pos = c.find('\n' + anchor) if anchor else -1
        if pos == -1:
            others.append((id_, src, body))
        else:
            c = c[:pos + 1] + quote(id_, src, body) + c[pos + 1:]
    ids = '、'.join(dict.fromkeys(b[0] for b in blocks if b[2]))
    head = f'\n\n---\n\n# 00 · 学员自定义认知（已合并）\n\n本文件已合并学员自己的 SMC 认知，覆盖的概念：{ids}。对应章节前的"【用户口径】"块优先于项目默认内容，按"用户自定义认知"规则使用。\n\n'
    head += ''.join(quote(*o) for o in others)
    i = c.index('\n\n---\n\n')  # 插在通用指令头之后
    c = c[:i] + head + c[i:]
    open('prompt/SMC-AI-Tutor.custom.md', 'w', encoding='utf-8').write(c)
    print('merged', len(blocks), 'user blocks →', 'prompt/SMC-AI-Tutor.custom.md')


# ---------- 2. 学习手册 ----------
def embed_images(t):
    out = []
    for ln in t.split('\n'):
        names = []
        for mo in re.finditer(r'（配图：[^）]*）', ln):
            names += re.findall(r'(\d\d-[^、）\s`]+)', mo.group(0))
        if names:
            ln = re.sub(r'（配图：[^）]*）', '', ln).rstrip()
            out.append(ln)
            for n in names:
                out += ['', f'![{n}](../diagrams/png/{n}.png)']
        else:
            out.append(ln)
    return '\n'.join(out)


p1 = read(R + '01-认知框架.md').replace('# 01 · SMC 认知框架（知识主干）', '# 第一部分　认知框架')
p1 = re.sub(r'\n> 这是整套教学的知识底稿[^\n]*\n', '\n', p1)
p1 = p1.replace('教学时先讲本口径，再说明差异', '学习时以本口径为准，遇到别处说法不同时注意区分')
p1 = p1.replace('不同社区对 CISD 的叫法和定义不完全一样，教学时说明这是本教程口径',
                '不同社区对 CISD 的叫法和定义不完全一样，这里是本手册的口径')

p2 = read(R + '02-常见疑问与回答.md').replace('# 02 · 常见 SMC 疑问与回答', '# 第二部分　常见疑问与回答')
p2 = re.sub(r'\n> 答疑时优先在这里找[^\n]*\n', '\n', p2)

p3 = read(R + '03-学习路径与练习.md').replace('# 03 · 学习路径与练习', '# 第三部分　学习路线与自测')
p3 = re.sub(r'\n> "系统学习"模式按这里的课程顺序推进。[^\n]*\n',
            '\n> 每节建议的学习节奏：读懂要点 → 对照示意图 → 做练习 → 做自测题。3 题答对 2 题以上再进入下一节。\n', p3)
p3 = p3.replace('**过关题**', '**自测题**').replace('## 练习题库（测验模式随机抽取）', '## 综合测验（15 题）')
p3 = re.sub(r'\n以下题目可用于"测验模式"[^\n]*\n', '\n学完全部课程后做一遍，答案在每题末尾括号里，建议先遮住再做。\n', p3)

p4 = read(R + '04-误区与清单.md').replace('# 04 · 常见误区与执行清单', '# 第四部分　常见误区与执行清单')



def embed_models(t, prefix):
    names = sorted(os.listdir('diagrams/models/png'))
    out = []
    for ln in t.split('\n'):
        out.append(ln)
        m = re.match(r'### ([AB])(\d+)\.', ln)
        if m:
            key = m.group(1) + (m.group(2).zfill(2) if m.group(1) == 'B' else m.group(2))
            hit = [n for n in names if n.startswith(key + '-')]
            if hit:
                out += ['', f'![{hit[0][:-4]}]({prefix}{hit[0]})']
    return '\n'.join(out)


p6 = read(R + '06-进阶概念与入场模型.md').replace('# 06 · 进阶概念与入场模型', '# 第五部分　进阶概念与入场模型')
p6 = re.sub(r'\n> 讲解时注意：[^\n]*\n', '\n', p6)
hb = '\n\n'.join([read('tools/handbook_front.md'), embed_images(p1), embed_images(p2), embed_images(p3), p4,
                   embed_models(p6, '../diagrams/models/png/')])

em = read(R + '06-进阶概念与入场模型.md').replace('# 06 · 进阶概念与入场模型', '# SMC 进阶概念与入场模型图鉴')
em = em.replace('> 本文件是进阶内容，学完 L0–L10 再学。分两部分：',
                '> 本文件由 `tools/build.py` 自动生成，可直接阅读，不需要 AI。建议先掌握 SMC 基础（结构、流动性、FVG、OB、区间、触发）再看。\n>\n> 分两部分：')
em = re.sub(r'\n> 讲解时注意：[^\n]*\n', '\n', em)
em += '\n\n---\n\n仅供学习交流，不构成任何投资建议。所有示意图为程序生成的虚构走势，非真实行情。\n'
open('docs/entry-models.md', 'w', encoding='utf-8').write(embed_models(em, '../diagrams/models/png/'))
open('docs/handbook.md', 'w', encoding='utf-8').write(hb)
print('built prompt/SMC-AI-Tutor.md, docs/handbook.md, docs/entry-models.md')
