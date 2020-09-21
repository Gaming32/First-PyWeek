import sys
import subprocess
import runpy


should_build = input('Would you like to build the game to make it run faster? [Y/n] ')
should_build = not should_build or should_build[0].lower == 'y'

if should_build:
    # The game should be built
    if subprocess.call([sys.executable, 'setup.py', 'build_ext']):
        print('The game could not be built, using non-built version'
              ' (Are Cython and setuptools installed?)')

runpy._run_module_as_main('game')
