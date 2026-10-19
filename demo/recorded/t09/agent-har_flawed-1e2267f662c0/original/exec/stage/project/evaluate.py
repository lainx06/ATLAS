"""UCI HAR, ATLAS-authored flawed variant (T-09). Not the dataset authors' protocol, and no flaw is
alleged in the original study.

Deliberate flaws, both ATLAS-authored:
1. the scaler and the feature selector are fit on every training row (all 21 training subjects)
   before any split, so each fold's evaluation rows shape the fitted state;
2. the folds are a random row-level KFold over windows, so the same subjects (and overlapping
   windows of the same recordings) sit on both sides of every fold.

Only the training partition is present in the table; the official test partition is never read.
"""

from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler

from atlas import adapter

X, y = adapter.load_table()
# Flaw 1 (ATLAS-authored): global fitting on all rows, before the split.
X_scaled = StandardScaler().fit_transform(X)
X_selected = SelectKBest(f_classif, k=50).fit_transform(X_scaled, y)
# Flaw 2 (ATLAS-authored): random row-level folds; subjects cross every fold.
folds = KFold(n_splits=5, shuffle=True, random_state=0).split(X_selected)
for k, (tr, ev) in enumerate(folds):
    train_ids, eval_ids = list(X.index[tr]), list(X.index[ev])
    adapter.declare_split(f"fold{k}", train_ids, eval_ids)
    model = LogisticRegression(max_iter=1000)
    model.fit(adapter.take(X_selected, train_ids), adapter.take(y, train_ids))
    adapter.write_predictions(
        f"fold{k}", eval_ids, model.predict(adapter.take(X_selected, eval_ids))
    )
