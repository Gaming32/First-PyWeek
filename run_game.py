import sys
import os
import subprocess
import shutil
import glob
import runpy


should_build = input('Would you like to build the game to make it run faster? [Y/n] ')
should_build = not should_build or should_build[0].lower == 'y'

if should_build:
    # The game should be built
    if subprocess.call([sys.executable, 'setup.py', 'build_ext']):
        print('The game could not be built, using non-built version'
              ' (Are Cython and setuptools installed?)')
    else:
        file_to_copy = next(glob.iglob('build/lib.*/*'))
        shutil.copyfile(file_to_copy, os.path.basename(file_to_copy))

runpy._run_module_as_main('game')
