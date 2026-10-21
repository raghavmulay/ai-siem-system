"""
ml/preprocessing.py
-------------------
HISTORICAL NOTE — DATA LEAKAGE BUG (now fixed)
-----------------------------------------------
The original version of this file concatenated train_df and test_df before
fitting LabelEncoders and StandardScaler, then split them back apart.
This caused data leakage: the scaler and encoders saw test-set values during
fitting, making evaluation metrics optimistic.

Current design
--------------
All preprocessing is now handled inside ml/train_model.py:
  - OrdinalEncoder fitted on training data only
  - StandardScaler fitted on training data only
  - LabelEncoder for targets fitted on training labels only
  - Fitted objects saved to backend/models/ for inference reuse

This file is kept as a compatibility shim so any external code that imports
`from ml.preprocessing import preprocess` receives a clear error rather than
silently running the leaky version.
"""


def preprocess(train_df, test_df):
    raise NotImplementedError(
        "ml.preprocessing.preprocess() has been retired to fix a data-leakage bug.\n"
        "Use ml/train_model.py directly:\n"
        "    python ml/train_model.py\n"
        "or via the convenience entry point:\n"
        "    python ml/main.py"
    )
