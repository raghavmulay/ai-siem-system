import pandas as pd
from ml.preprocessing import preprocess
from ml.train_model import train_models

train_df = pd.read_csv("ml/data/train.csv")
test_df = pd.read_csv("ml/data/test.csv")

X_train, X_test, y_train, y_test = preprocess(train_df, test_df)

train_models(X_train, y_train, X_test, y_test)

print("Testing Complete 🚀")

print("Feature count:", X_train.shape[1])