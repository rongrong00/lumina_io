"""Copy the sphinx-markdown-builder output into docs/markdown/, escaping
pseudo-HTML tokens like <root> or <Field> (outside code fences) that
GitHub's Markdown renderer would otherwise treat as unknown HTML tags and
hide.

Usage:  sphinx-build -b markdown docs docs/_build/md
        python docs/postprocess_md.py
"""

import glob
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '_build', 'md')
OUT = os.path.join(HERE, 'markdown')


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    for src in glob.glob(SRC + '/**/*.md', recursive=True):
        dst = os.path.join(OUT, os.path.relpath(src, SRC))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        out, fenced = [], False
        for line in open(src):
            if line.lstrip().startswith('```'):
                fenced = not fenced
            elif not fenced:
                line = re.sub(r'<([A-Za-z_][\w./*-]*)>', r'`<\1>`', line)
            out.append(line)
        open(dst, 'w').writelines(out)
        print('wrote', os.path.relpath(dst, HERE))


if __name__ == '__main__':
    main()
