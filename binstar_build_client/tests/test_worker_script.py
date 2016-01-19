'''
Created on Feb 18, 2014

@author: sean
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import os
import yaml
from mock import patch
import unittest

from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_build_client.scripts.worker import main
from binstar_build_client.worker.register import WorkerConfiguration
from glob import glob
from binstar_client import errors

test_workers = os.path.abspath('./test-workers')
worker_data = {
               'username': 'username',
               'queue': 'queue-1',
               'platform': 'platform',
               'worker_id': 'worker_id',
               'hostname': 'localhost',
               'dist': 'dist',
            }

class Test(CLITestCase):

    @classmethod
    def setUpClass(cls):
        WorkerConfiguration.REGISTERED_WORKERS_DIR = test_workers
        if not os.path.exists(WorkerConfiguration.REGISTERED_WORKERS_DIR):
            os.mkdir(WorkerConfiguration.REGISTERED_WORKERS_DIR)
        super(Test, cls).setUpClass()

    def tearDown(self):

        for fn in glob(os.path.join(test_workers, '*')):
            os.unlink(fn)

        unittest.TestCase.tearDown(self)

    @urlpatch
    @patch('binstar_build_client.worker.register.WorkerConfiguration.register')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.deregister')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.load')
    def test_register(self, load, deregister, urls, register):

        main(['register', 'username/queue-1'], False)
        self.assertEqual(register.call_count, 1)

        main(['deregister', 'worker_id'], False)
        self.assertEqual(deregister.call_count, 1)

    @urlpatch
    @patch('binstar_build_client.worker.worker.Worker.work_forever')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.load')
    @patch('binstar_build_client.worker.worker.Worker.run')
    def test_worker_simple(self, run, load, loop, urls):

        main(['--show-traceback', 'worker', 'run', worker_data['worker_id']], False)

        self.assertEqual(loop.call_count, 1)

    def test_register_backwards_compat(self):

        worker_file = os.path.join(WorkerConfiguration.REGISTERED_WORKERS_DIR,
                                   'worker_name_1')
        worker_id = '123456789'
        worker_id_pid = '{}.123'.format(worker_id)
        try:
            with open(worker_id_pid, 'w') as f:
                f.write('') # make sure a PID file's presence
                            # is non-breaking
            with open(worker_file, 'w') as f:
                f.write(yaml.safe_dump({'worker_id': worker_id}))
            worker_id_to_name = WorkerConfiguration.backwards_compat_lookup()
            self.assertIn(worker_id, worker_id_to_name)
            self.assertEqual(worker_id_to_name[worker_id], 'worker_name_1')
        finally:
            if os.path.exists(worker_file):
                os.unlink(worker_file)
        worker_id_to_name = WorkerConfiguration.backwards_compat_lookup()
        self.assertEqual(worker_id_to_name.get(worker_id, None), None)

if __name__ == '__main__':
    unittest.main()
