"""UCI HAR clean control (T-09): folds grouped by subject within the training subjects, and the
scaler, selector and classifier all fit inside each fold on its training rows only.

The same model family as the ATLAS-authored flawed variant (har_flawed). Only the training
partition is present in the table; the official test partition is never read.
"""

from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from atlas import adapter

X, y = adapter.load_table()
subjects = adapter.load_metadata().loc[X.index, "subject_id"]
for k, (tr, ev) in enumerate(GroupKFold(n_splits=5).split(X, y, subjects)):
    train_ids, eval_ids = list(X.index[tr]), list(X.index[ev])
    adapter.declare_split(f"fold{k}", train_ids, eval_ids)
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("select", SelectKBest(f_classif, k=50)),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    model.fit(adapter.take(X, train_ids), adapter.take(y, train_ids))
    adapter.write_predictions(
        f"fold{k}", eval_ids, model.predict(adapter.take(X, eval_ids))
    )
