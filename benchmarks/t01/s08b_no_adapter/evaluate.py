"""s08b: a plain scikit-learn script that does not use the ATLAS adapter."""

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

table = pd.read_csv("table.csv")
X = table[[f"f{i}" for i in range(6)]]
print(cross_val_score(LogisticRegression(), X, table["activity"], cv=4).mean())
