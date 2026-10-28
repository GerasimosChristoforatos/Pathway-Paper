"""AST equivalence of the Python files of two revisions: a change that only touches comments and docstrings leaves the
module's abstract syntax tree unchanged.

For every .py file present in both the base revision (a git ref) and the working tree, the module is parsed, every
docstring is stripped (the first statement of a module, class, function or async function when it is a string
constant) and ast.dump of the result is compared; comments are not part of the AST. A file whose dumps differ is
reported with the top-level definitions (functions, classes, assignments by target name) that were added, removed or
changed. Files present only on one side are listed.

    python tools/ast_equivalence.py <base ref> [--expect FILE ...]

Exit 1 if a file outside --expect differs (files where code was removed on purpose are passed with --expect and
reported in full).
"""
import argparse
import ast
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def strip_docstrings(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return tree


def dump(src):
    return ast.dump(strip_docstrings(ast.parse(src)), include_attributes=False)


def top_level(src):
    """{name: dump} of the top-level statements (definitions by name, other statements by position)."""
    out = {}
    for k, node in enumerate(strip_docstrings(ast.parse(src)).body):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            key = f'{type(node).__name__} {node.name}'
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            tg = node.targets if isinstance(node, ast.Assign) else [node.target]
            key = 'assign ' + ', '.join(ast.unparse(t) for t in tg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            key = 'import ' + ast.unparse(node)
        else:
            key = f'{type(node).__name__} {ast.unparse(node)[:60]!r}'
        while key in out:
            key += "'"
        out[key] = ast.dump(node, include_attributes=False)
    return out


def files_at(ref):
    r = subprocess.run(['git', 'ls-tree', '-r', '--name-only', ref], cwd=ROOT, capture_output=True, text=True,
                       check=True)
    return {f for f in r.stdout.split() if f.endswith('.py')}


def show(ref, path):
    return subprocess.run(['git', 'show', f'{ref}:{path}'], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('base')
    p.add_argument('--expect', nargs='*', default=[], help='files where code was removed on purpose')
    a = p.parse_args(argv)
    before = files_at(a.base)
    now = {os.path.relpath(os.path.join(d, f), ROOT) for d, _, fs in os.walk(ROOT) for f in fs
           if f.endswith('.py') and '.git' not in d and '__pycache__' not in d and not d.startswith(
               os.path.join(ROOT, 'outputs'))}
    common = sorted(before & now)
    same, diff = [], []
    for f in common:
        old, new = show(a.base, f), open(os.path.join(ROOT, f)).read()
        (same if dump(old) == dump(new) else diff).append(f)
    print(f'ast_equivalence vs {a.base}: {len(common)} files in both; {len(same)} equivalent; {len(diff)} differ')
    bad = []
    for f in diff:
        t0, t1 = top_level(show(a.base, f)), top_level(open(os.path.join(ROOT, f)).read())
        removed = [k for k in t0 if k not in t1]
        added = [k for k in t1 if k not in t0]
        changed = [k for k in t0 if k in t1 and t0[k] != t1[k]]
        tag = 'expected' if f in a.expect else 'UNEXPECTED'
        if f not in a.expect:
            bad.append(f)
        print(f'  {tag}: {f}')
        for lab, ks in (('removed', removed), ('added', added), ('changed', changed)):
            for k in ks:
                print(f'      {lab}: {k}')
    gone, new_files = sorted(before - now), sorted(now - before)
    print(f'deleted files ({len(gone)}): ' + ', '.join(gone))
    print(f'new files ({len(new_files)}): ' + ', '.join(new_files))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
