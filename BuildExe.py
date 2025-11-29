import PyInstaller.__main__
import shutil
import os

filename = ''     # Name of the Python file to convert
exename = ''      # Output EXE name
icon = ''         # Optional: icon file
pwd = os.getcwd()
dist = os.path.join(pwd, 'dist')

PyInstaller.__main__.run([
    '--onefile',
    '--noconsole',
    '--name=%s' % exename,
    '--icon=%s' % icon,
    filename
])

# Clean up after build
shutil.move(os.path.join(dist, exename), pwd)
shutil.rmtree('dist')
shutil.rmtree('build')
shutil.rmtree('__pycache__')
os.remove(exename + '.spec')
