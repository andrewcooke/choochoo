
import webbrowser as wb
from os.path import join

import nbformat as nb
import nbformat.v4 as nbv
from notebook.notebookapp import NotebookApp


class Notebook:

    def __init__(self, log, filename, title):
        self._log = log
        self._filename = filename
        if '.' not in self._filename:
            self._filename += '.ipynb'
        self._notebook = nbv.new_notebook()
        self._notebook['cells'].append(nbv.new_markdown_cell("# %s" % title))

    def display(self):
        path = join(NotebookApp.instance().notebook_dir, self._filename)
        with open(path, 'w') as out:
            nb.write(self._notebook, out)
        wb.open('http://localhost:8888/tree/%s' % self._filename)
