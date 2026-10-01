#!/usr/bin/env python3
"""Offline unittest plus the supplied function-style fixtures, with temporary keys."""
import inspect
import os
import sys
import tempfile
import unittest
from pathlib import Path

if __name__=='__main__':
    if not __debug__:
        raise RuntimeError('run tests without -O; function-style assertions must remain active')
    with tempfile.TemporaryDirectory(prefix='klstream-factory-test-keys-') as key_dir:
        class IsolatedKeyResult(unittest.TextTestResult):
            def startTest(self,test):
                self.test_keys=tempfile.TemporaryDirectory(prefix='case-',dir=key_dir)
                os.environ['FACTORY_SUPERVISOR_KEY']=str(Path(self.test_keys.name)/'supervisor.key')
                super().startTest(test)
            def stopTest(self,test):
                try:super().stopTest(test)
                finally:self.test_keys.cleanup()
        folder=Path(__file__).parent/'tests'
        suite=unittest.defaultTestLoader.discover(str(folder),pattern='test_*.py')
        # unittest discovery omits module-level pytest-style test functions.
        # These supplied fixtures need only the tmp_path argument, so no pytest
        # dependency is required to execute them honestly in the same runner.
        for file in sorted(folder.glob('test_*.py')):
            module=sys.modules[file.stem]
            for name,function in inspect.getmembers(module,inspect.isfunction):
                if not name.startswith('test_') or function.__module__!=module.__name__:continue
                def run_function(function=function):
                    parameters=list(inspect.signature(function).parameters)
                    if parameters==['tmp_path']:
                        with tempfile.TemporaryDirectory(prefix='klstream-function-test-') as directory:
                            function(Path(directory))
                    elif not parameters:function()
                    else:raise RuntimeError('unsupported fixture parameters: '+str(parameters))
                suite.addTest(unittest.FunctionTestCase(run_function,description=file.stem+'.'+name))
        result=unittest.TextTestRunner(verbosity=2,resultclass=IsolatedKeyResult).run(suite)
        raise SystemExit(0 if result.wasSuccessful() else 1)
