import os
import logging
import time
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import PyInstaller.__main__


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


start = time.perf_counter()
pyinstaller_start = time.perf_counter()
logger.info('Running PyInstaller build method...')
PyInstaller.__main__.run([
    'app.spec',
    '--noconfirm'
])
logger.info(f'PyInstaller successfully built app at dist/app ({(time.perf_counter() - pyinstaller_start):.2f}s)')

zip_start = time.perf_counter()
logger.info('Building zip file at dist/app.zip...')
with ZipFile('dist/app.zip', 'w', ZIP_DEFLATED) as zipfile:
    path = Path('dist/app')
    files = list(path.rglob('*'))
    for index, file in enumerate(files, start=1):
        zipfile.write(file, file.relative_to(path))
        logger.info(f'Adding {file.name} to zip archive ({index}/{len(files)})')
logger.info(f'Zip file at dist/app.zip was created successfully ({(time.perf_counter() - zip_start):.2f}s)')

nsis_start = time.perf_counter()
logger.info('Compiling nsis installer...')
os.system('makensis install.nsi')
logger.info(f'NSIS installer compiled at SpotAlong-Installer.exe ({(time.perf_counter() - nsis_start):.2f}s)')
logger.info(f'Build finished ({(time.perf_counter() - start):.2f}s)')
os.remove('dist/app.zip')
