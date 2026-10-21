"""
ml/main.py
----------
Convenience entry point.  All training logic lives in ml/train_model.py.

Previous issue: this file called train_models(X_train, y_train, X_test, y_test)
with 4 positional arguments, but the function required 7.  That caused an
immediate TypeError on every run.

Fix: ml/train_model.py is now a self-contained script with its own __main__
block.  This file simply imports and runs it so both entry points work:

    python ml/main.py          # via this file
    python ml/train_model.py   # directly
    python -m ml.train_model   # as a module
"""

import runpy
import os

if __name__ == "__main__":
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "train_model.py")
    runpy.run_path(script, run_name="__main__")
