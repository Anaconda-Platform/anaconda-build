

import os
import sys
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

CONDA_EXE = 'conda.exe' if os.name == 'nt' else 'conda'

def get_conda_root_prefix():
    """
    get the directory prefix to where conda is installed
    """
    canonical_dir_current_executable = os.path.dirname(os.path.realpath(sys.executable))
    paths = [canonical_dir_current_executable, ] + os.environ.get('PATH').split(os.pathsep)

    for entry in paths:
        if os.path.isdir(entry) and CONDA_EXE in os.listdir(entry):
            conda_exe_path = os.path.realpath(os.path.join(entry, 'conda'))
            bin_dir = os.path.dirname(conda_exe_path)
            return os.path.dirname(bin_dir)

def get_anaconda_url(binstar):
    netloc = urlparse(binstar.domain).netloc
    if netloc.startswith('api.'):
        netloc = netloc.replace('api.', '')
    return netloc
