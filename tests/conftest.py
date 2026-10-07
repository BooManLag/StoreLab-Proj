import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Tests never call the real Gemini API.
os.environ["STORELAB_AGENT_MODE"] = "offline"


@pytest.fixture(scope="session")
def world():
    from storelab.world import get_world

    return get_world()
