"""从 skills/smc-learning/references/ 生成：
  prompt/SMC-AI-Tutor.md  —— 单文件通用 AI 指令（任意 AI 可用）
  docs/handbook.md        —— 给人读的学习手册（嵌入示意图）
在仓库根目录运行：python3 tools/build.py
"""
import re

R = 'skills/smc-learning/references/'


def read(path):
    return open(path, encoding='utf-8').read()


# ---------- 1. 通用 AI 指令 ----------
ascii_map = {'01': '4.1', '02': '4.2', '03': '4.3', '04': '4.4', '05': '4.5', '06': '4.6',
             '07': '4.7', '08': '4.8', '09': '4.3', '10': '4.9'}


def to_ascii_ref(t):
    def rep(mo):
        ids = re.findall(r'(\d\d)-', mo.group(0))
        refs = sorted({ascii_map[i] for i in ids if i in ascii_map})
        return f'（字符图 {"、".join(refs)}）' if refs else ''
    return re.sub(r'（配图：[^）]*）', rep, t)


parts = [read('tools/universal_header.md')]
for f in ['01-认知框架.md', '02-常见疑问与回答.md', '03-学习路径与练习.md', '04-误区与清单.md']:
    parts.append(to_ascii_ref(read(R + f)))
t = read(R + '05-画图规范.md')
t = t[t.index('## 三、现画 SVG 的规范'):]
t = '# 05 · 画图规范\n\n' + t.replace(
    '需要画现成图里没有的场景（例如学员描述的某种走势）时，按以下约定，保证风格一致：',
    '能渲染 SVG 时，按以下约定画图，保证风格一致：')
parts.append(t)
u = '\n\n---\n\n'.join(parts)
u = u.replace('| 课 | 主题 | 核心问题 | 配图 |', '| 课 | 主题 | 核心问题 | 字符图 |')
for a, b in [('| 00 |', '| — |'), ('| 01 |', '| 4.1 |'), ('| 02 |', '| 4.2 |'), ('| 03、09 |', '| 4.3 |'),
             ('| 04 |', '| 4.4 |'), ('| 05 |', '| 4.5 |'), ('| 06 |', '| 4.6 |'), ('| 07 |', '| 4.7 |'),
             ('| 08、10 |', '| 4.8、4.9 |'), ('| 00、08 |', '| 4.8 |')]:
    u = u.replace(a, b)
open('prompt/SMC-AI-Tutor.md', 'w', encoding='utf-8').write(u)


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

hb = '\n\n'.join([read('tools/handbook_front.md'), embed_images(p1), embed_images(p2), embed_images(p3), p4])
open('docs/handbook.md', 'w', encoding='utf-8').write(hb)
print('built prompt/SMC-AI-Tutor.md and docs/handbook.md')
