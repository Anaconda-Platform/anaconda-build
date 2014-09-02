"""
Popen module with buffered IO 

i.e. stdout, stderr can be any file 'like' object. Like an io.BytesIO() object

Also this adds a new keyword argument iotimeout which will terminate the process if no output is recieved for 
iotimeout seconds  
"""

from __future__ import print_function

import logging
import os
import platform
import select
import signal
from subprocess import Popen, PIPE
from threading import Thread
import time


log = logging.getLogger('binstar.build')

def read_ready(fds, timeout=0.1):
    """
    Wait for any of the fds to be ready to read 
    """
    read_fds = select.select([fd for fd in fds if fd], [], [], timeout)[0]
    return [fd if fd in read_fds else None for fd in fds]

def run(proc, out_pipe, stdout, err_pipe, stderr, timeout=None):
    """
    While proc (A Popen object) is alive wait for output to be recieved from
    out_pipe or err_pipe and write it to stdout and stderr respectively
    
    If timeout is given, and no output is recieved after timeout seconds proc will
    be terminated 
    """

    last_ready = time.time()
    while 1:
        std_out_ready, std_err_ready = read_ready([out_pipe[0], err_pipe[0]])
        if std_out_ready:
            last_ready = time.time()
            out_data = os.read(out_pipe[0], 512)
            if not out_data: continue
            stdout.write(out_data)
        else:
            out_data = ''
        if std_err_ready:
            last_ready = time.time()
            err_data = os.read(err_pipe[0], 512)
            if not err_data: continue
            stderr.write(err_data)
        else:
            err_data = ''

        if out_data or err_data: continue  # Keep reading/ don't exit
        if proc.poll() is not None:  # select timeout
            break  # proc exited
        if timeout and (time.time() - last_ready) > timeout:
            log.info("Timeout: No output from program for %s seconds" % timeout)
            log.info("Terminating Build")

            if is_normal(stderr):
                out = stderr
            elif is_normal(stdout):
                out = stdout
            else:
                break

            out.write("\nTimeout: No output from program for %s seconds\n" % timeout)
            out.write("\nTimeout: If you require a longer timeout you "
                      "may set the 'iotimeout' variable in your .binstar.yml file\n")
            out.write("[Terminating]\n")
            proc.send_signal(signal.SIGTERM)
            break


    if out_pipe[0]: os.close(out_pipe[0])
    if out_pipe[1]: os.close(out_pipe[1])
    if err_pipe[0]: os.close(err_pipe[0])
    if err_pipe[1]: os.close(err_pipe[1])


def is_special(stdio):
    return (stdio is None) or (isinstance(stdio, int) and stdio < 0)

def is_normal(stdio):
    return not is_special(stdio)

class BufferedPopen(Popen):
    def __init__(self, args, iotimeout=None, stdout=PIPE, stderr=PIPE, bufsize=1, close_fds=True, **kwargs):

        _stdout, _stderr = stdout, stderr
        self._stdout_pipe = [None, None]
        self._stderr_pipe = [None, None]
        if is_normal(stdout):
            self._stdout_pipe = os.pipe()  # provide tty to enable
            stdout = self._stdout_pipe[1]

        if is_normal(stderr):
            self._stderr_pipe = os.pipe()  # provide tty to enable
            stderr = self._stderr_pipe[1]

        if platform.system() == 'Windows':
            close_fds = False

        Popen.__init__(self, args, bufsize=bufsize,
                       stdout=stdout, stderr=stderr,
                       close_fds=close_fds, **kwargs)

        if is_normal(stdout):
            self.stdout = _stdout

        if is_normal(stderr):
            self.stderr = _stderr

        run_args = (self, self._stdout_pipe, _stdout,
                          self._stderr_pipe, _stderr,
                    iotimeout)

        if is_normal(_stderr) or is_normal(_stdout):
            t = Thread(target=run, name='BufferedPopen_run', args=run_args)
            self._thread = t
            t.start()
        else:
            self._thread = None

    def wait(self):
        exitcode = Popen.wait(self)
        if self._thread and self._thread.isAlive():
            self._thread.join()
        return exitcode


