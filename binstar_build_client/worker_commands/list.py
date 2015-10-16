'''
List Anaconda build workers

anaconda worker list
'''
from __future__ import (print_function, unicode_literals, division,
    absolute_import)


from binstar_client.utils import get_binstar

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.register import print_registered_workers


def main(args):
    bs = get_binstar(args, cls=BinstarBuildAPI)
    print_registered_workers()

def add_parser(subparsers, name='list',
               description='List build workers and queues',
               epilog=__doc__):
    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )
    parser.set_defaults(main=main)

    return parser