"""s10c_known_duplicate: the s02 clean protocol; this scenario differs only in its manifest or table."""

from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from atlas import adapter

X, y = adapter.load_table()
groups = adapter.load_metadata().loc[X.index, "subject_id"]
for k, (tr, ev) in enumerate(GroupKFold(n_splits=4).split(X, y, groups)):
    train_ids, eval_ids = list(X.index[tr]), list(X.index[ev])
    adapter.declare_split(f"fold{k}", train_ids, eval_ids)
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("select", SelectKBest(f_classif, k=3)),
            ("clf", LogisticRegression()),
        ]
    )
    model.fit(adapter.take(X, train_ids), adapter.take(y, train_ids))
    adapter.write_predictions(
        f"fold{k}", eval_ids, model.predict(adapter.take(X, eval_ids))
    )
