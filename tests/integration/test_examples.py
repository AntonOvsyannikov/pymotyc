import subprocess
import sys
from glob import glob
from pathlib import Path

import pytest

examples = glob(str(Path(__file__, *['..'] * 3, 'examples').resolve()) + '/**/*.py', recursive=True)


@pytest.mark.parametrize('example', examples)
def test_example(example):
    assert not subprocess.call([sys.executable, example])
