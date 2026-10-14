"""s03b: like s02, but a tracked training frame is modified in place before fitting."""

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
    X_train = adapter.take(X, train_ids)
    X_train.iloc[:, 0] = X_train.iloc[:, 0] * 1.5
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("select", SelectKBest(f_classif, k=3)),
            ("clf", LogisticRegression()),
        ]
    )
    model.fit(X_train, adapter.take(y, train_ids))
    adapter.write_predictions(
        f"fold{k}", eval_ids, model.predict(adapter.take(X, eval_ids))
    )
