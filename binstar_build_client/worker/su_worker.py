"""
SuWorker in this module is a subclass of worker.worker for
the purpose of running a root python build process that does each
build as a lesser user, build_user, via su.  SuWorker must
be run as root with a root python install.
"""
from __future__ import print_function, absolute_import, unicode_literals

import io
import logging
import os
import pipes
import shutil

from binstar_client import errors
from binstar_client.utils import get_config

from binstar_build_client.utils.rm import rm_rf
from binstar_build_client.worker.utils.buffered_io import BufferedPopen
from binstar_build_client.worker.worker import Worker

SU_WORKER_DEFAULT_PATH = '/opt/anaconda'

log = logging.getLogger('binstar.build')


def cmd(cmd):
    stdout = io.StringIO()
    proc = BufferedPopen(cmd, stdout=stdout)
    proc.wait()
    return stdout.getvalue()


def check_conda_path(build_user, python_install_dir):
    conda_exe = os.path.join(python_install_dir, 'bin', 'conda')
    check_conda = "{} && echo has_conda_installed".format(conda_exe)
    conda_output = cmd(['su', '--login', '-c', check_conda, '-', build_user])
    if 'has_conda_installed' not in conda_output:
        raise errors.BinstarError('Did not find conda at {}'.format(conda_exe))
    return True


def test_su_as_user(build_user):
    whoami_as_user = cmd(['su', '--login', '-c', 'whoami', '-', build_user]).strip()
    has_build_user = build_user in whoami_as_user
    if not has_build_user:
        info = (build_user, whoami_as_user)
        raise errors.BinstarError('Cannot continue without build_user {}.'
                                  ' Got whoami = {}'.format(*info))
    return True


def validate_su_worker(build_user, python_install_dir):
    '''Ensure su_worker is running as root, that there is a build worker, that
    /etc/worker-skel exists, and that conda is accessible to the build_user.'''
    if build_user == 'root':
        raise errors.BinstarError('Do NOT make root the build_user.  '
                                  'The home directory of build_user is DELETED.')
    has_etc_worker_skel = os.path.isdir('/etc/worker-skel')
    if not has_etc_worker_skel:
        raise errors.BinstarError('Expected /etc/worker-skel to exist and '
                                  'be a template for {}\'s'
                                  ' home directory'.format(build_user))
    is_root = os.getuid() == 0
    if not is_root:
        raise errors.BinstarError('Expected su_worker to run as root.')
    return test_su_as_user(build_user) and check_conda_path(build_user,
                                                            python_install_dir)


class SuWorker(Worker):
    '''Overrides the run method of Worker to run builds
    as a lesser user. '''

    def __init__(self, bs, args, build_user, python_install_dir):
        super(SuWorker, self).__init__(bs, args)
        self.build_user = build_user
        self.python_install_dir = python_install_dir
        validate_su_worker(self.build_user, self.python_install_dir)

    @property
    def source_env(self):
        return "export PATH={}/bin:${PATH} ".format(self.python_install_dir) + \
                "&& source activate anaconda.org "

    def _finish_job(self, job_data, failed, status):
        '''Count job as finished, destroy build user processes,
        and replace build user's home directory'''
        self.destroy_user_procs()
        self.clean_home_dir()
        super(SuWorker, self)._finish_job(job_data, failed, status)

    @property
    def anaconda_url(self):
        config = get_config(remote_site=self.args.site)
        return config.get('url', 'https://api.anaconda.org')

    def su_with_env(self, cmd):
        '''args for su as build_user with the anaconda settings'''
        cmds = ['su', '--login', '-c', self.source_env]
        cmds[-1] += " && anaconda config --set url {} && ".format(self.anaconda_url)
        cmds[-1] += cmd
        cmds += ['-', self.build_user]
        return cmds

    def clean_home_dir(self):
        '''Delete lesser build_user's home dir and
        replace it with /etc/worker-skel'''
        home_dir = os.path.expanduser('~{}'.format(self.build_user))
        log.info('Remove build worker home directory: {}'.format(home_dir))
        rm_rf(home_dir)
        shutil.copytree('/etc/worker-skel', home_dir, symlinks=False)
        out = cmd(['chown', '-R', "{}:{}".format(self.build_user, self.build_user), home_dir])
        if out:
            log.info(out)
        log.info('Copied /etc/worker-skel to {}.  Changed permissions.'.format(home_dir))

    def destroy_user_procs(self):
        log.info("Destroy {}'s processes".format(self.build_user))
        out = cmd(['pkill', '-U', self.build_user])
        if out:
            log.info(out)

    def run(self, build_data, script_filename, build_log, timeout, iotimeout,
            api_token=None, git_oauth_token=None, build_filename=None, instructions=None):

        log.info("Running build script")

        working_dir = self.working_dir(build_data)

        args = [os.path.abspath(script_filename), '--api-token', api_token]

        if git_oauth_token:
            args.extend(['--git-oauth-token', git_oauth_token])

        elif build_filename:
            args.extend(['--build-tarball', build_filename])

        log.info("Running command: (iotimeout={})".format(iotimeout))

        args = self.su_with_env(" ".join(pipes.quote(arg) for arg in args))
        log.info(args)
        p0 = BufferedPopen(args, stdout=build_log, iotimeout=iotimeout, cwd=working_dir)

        try:
            exit_code = p0.wait()
        except BaseException:
            log.error("Binstar build process caught an exception while waiting for the build to finish")
            self.destroy_user_procs()
            raise
        finally:
            self.destroy_user_procs()
            if p0.stdout and not p0.stdout.closed:
                log.info("Closing subprocess stdout PIPE")
                p0.stdout.close()
        return exit_code
