"""Create source.zip with the exact files expected by the client."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


root = Path(__file__).resolve().parent
target = root / 'source.zip'
with ZipFile(target, 'w', ZIP_DEFLATED) as archive:
    for name in ('strategy.py', 'README.md'):
        archive.write(root / name, name)
print(target)
