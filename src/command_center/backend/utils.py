import os
import threading
from typing import Optional

LLM_SEMAPHORE = threading.Semaphore(2)
