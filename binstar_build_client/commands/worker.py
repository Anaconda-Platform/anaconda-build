'''
Build worker 
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from argparse import Namespace
import logging
import os
import time
import yaml

from binstar_client.utils import get_binstar
from binstar_client import errors

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.worker import Worker
from binstar_build_client.worker.register import REGISTERED_WORKERS_DIR, print_registered_workers

log = logging.getLogger('binstar.build')

def main(args):
    worker_file = os.path.join(REGISTERED_WORKERS_DIR, args.worker_id)
    if not os.path.exists(worker_file):
        print_registered_workers()
        raise errors.BinstarError('Could not find worker config file at {}. See anaconda build register --help.')
    with open(worker_file) as f:
        worker_config = yaml.load(f.read())
    vars(args).update(worker_config)
    args.conda_build_dir = args.conda_build_dir.format(args=args)
    bs = get_binstar(args, cls=BinstarBuildAPI)

    log.info('Starting worker:')
    log.info('User: {}'.format(args.username))
    log.info('Queue: {}'.format(args.queue))
    log.info('Platform: {}'.format(args.platform))

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
                        help='Developers only, always push the build *back* onto the build queue')

    parser.set_defaults(main=main)
    return parser