
from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import os
from subprocess import check_output, CalledProcessError
try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'r+b')

class ExcludeGit(object):
    def __init__(self, path, use_git_ignore=True):
        self.path = os.path.abspath(path)
        try:
            filelist = check_output(['git', 'ls-files'], stderr=DEVNULL, cwd=self.path).decode().split()
            self.to_include = [ os.path.abspath(os.path.join(self.path, fn))
                                for fn in filelist ]
        except CalledProcessError as err:
            self.to_include = None

        self.num_included = 0

    def __call__(self, filename):
        filename = os.path.abspath(filename)
        if os.path.isdir(filename):
            return False

        if self.to_include is None or filename in self.to_include:
            self.num_included += 1
            return False

        return True
