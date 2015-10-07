'''
Build worker 
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging
import os
import yaml

from binstar_client.utils import get_binstar

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.utils import get_conda_root_prefix
from binstar_build_client.worker.worker import Worker
from binstar_build_client.worker.register import add_worker_options

log = logging.getLogger('binstar.build')


def main(args):

    add_worker_options(args)

    bs = get_binstar(args, cls=BinstarBuildAPI)

    worker = Worker(bs, args)

    worker.write_status(True, "Starting")

    try:
        worker.work_forever()
    finally:
        worker.write_status(False, "Exited")


def add_parser(subparsers, name='worker',
               description='Run a build worker to build jobs off of a binstar build queue',
               epilog=__doc__):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )
    parser.add_argument('worker_id',
                        help="worker_id that was given in anaconda build register")
    parser.add_argument('-f', '--fail', action='store_true',
                        help='Exit main loop on any un-handled exception')
    parser.add_argument('-1', '--one', action='store_true',
                        help='Exit main loop after only one build')
    parser.add_argument('--push-back', action='store_true',
                        help='Developers only, always push the build *back* ' + \
                             'onto the build queue')
    dgroup = parser.add_argument_group('development options')

    dgroup.add_argument("--conda-build-dir",
                        default=os.path.join(get_conda_root_prefix(),
                                             'conda-bld', '{args.platform}'),
                        help="[Advanced] The conda build directory (default: %(default)s)",
                        )
    dgroup.add_argument('--show-new-procs', action='store_true', dest='show_new_procs',
                        help='Print any process that started during the build '
                             'and is still running after the build finished')

    dgroup.add_argument('--status-file',
                        help='If given, binstar will update this file with the ' + \
                             'time it last checked the anaconda server for updates')

    parser.set_defaults(main=main)
    return parser
