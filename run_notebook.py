"""
Executes CELLS from cells.py against healthcare_bi.db and writes a real,
already-executed .ipynb file -- without needing nbformat/jupyter installed
(no network access to pip install them in this sandbox), by constructing the
notebook JSON directly per the nbformat v4 spec.
"""
import ast
import base64
import io
import json
import sys
import contextlib

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from cells import CELLS

ns = {}
notebook_cells = []
exec_count = 0

def fig_to_output(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=110)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('ascii')
    return {
        "output_type": "display_data",
        "data": {
            "image/png": b64,
            "text/plain": ["<Figure size {}x{} with 1 Axes>".format(*[int(v*fig.dpi) for v in fig.get_size_inches()])]
        },
        "metadata": {"image/png": {"width": int(fig.get_size_inches()[0]*fig.dpi), "height": int(fig.get_size_inches()[1]*fig.dpi)}}
    }

def value_to_execute_result(value, count):
    data = {}
    if isinstance(value, (pd.DataFrame, pd.Series)):
        data["text/plain"] = str(value).split("\n")
        try:
            data["text/html"] = [value.to_frame().to_html() if isinstance(value, pd.Series) else value.to_html()]
        except Exception:
            pass
    else:
        data["text/plain"] = repr(value).split("\n")
    return {
        "output_type": "execute_result",
        "execution_count": count,
        "data": {k: (v if isinstance(v, list) else [v]) for k, v in data.items()},
        "metadata": {}
    }

for cell_type, source in CELLS:
    if cell_type == "markdown":
        notebook_cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": source.splitlines(keepends=True)
        })
        continue

    exec_count += 1
    outputs = []
    stdout_buf = io.StringIO()
    stderr_text = None

    tree = ast.parse(source, mode='exec')
    last_expr = None
    body = tree.body
    if body and isinstance(body[-1], ast.Expr):
        last_expr = body.pop()

    module_no_last = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module_no_last)

    try:
        with contextlib.redirect_stdout(stdout_buf):
            exec(compile(module_no_last, filename="<cell>", mode="exec"), ns)
            result_value = None
            if last_expr is not None:
                expr_module = ast.Expression(body=last_expr.value)
                ast.fix_missing_locations(expr_module)
                result_value = eval(compile(expr_module, filename="<cell>", mode="eval"), ns)
    except Exception:
        import traceback
        stderr_text = traceback.format_exc()
        result_value = None

    text = stdout_buf.getvalue()
    if text:
        outputs.append({
            "output_type": "stream",
            "name": "stdout",
            "text": text.splitlines(keepends=True)
        })

    if stderr_text:
        outputs.append({
            "output_type": "error",
            "ename": "Error",
            "evalue": "cell raised an exception",
            "traceback": stderr_text.splitlines()
        })
        print(f"ERROR in cell {exec_count}:\n{stderr_text}", file=sys.stderr)

    fignums = plt.get_fignums()
    for n in fignums:
        fig = plt.figure(n)
        outputs.append(fig_to_output(fig))
    plt.close('all')

    if result_value is not None:
        outputs.append(value_to_execute_result(result_value, exec_count))

    notebook_cells.append({
        "cell_type": "code",
        "execution_count": exec_count,
        "metadata": {},
        "outputs": outputs,
        "source": source.splitlines(keepends=True)
    })

notebook = {
    "cells": notebook_cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"}
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

with open('/tmp/nb_run/healthcare_bi_reports.ipynb', 'w') as f:
    json.dump(notebook, f, indent=1)

print("Notebook written:", len(notebook_cells), "cells,", exec_count, "executed code cells")
