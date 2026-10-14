"""s05a: grouped folds, but a selector fit in fold 0 is reused in later folds whose eval subjects it learned from."""

from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

from atlas import adapter

X, y = adapter.load_table()
groups = adapter.load_metadata().loc[X.index, "subject_id"]
selector = None
for k, (tr, ev) in enumerate(GroupKFold(n_splits=4).split(X, y, groups)):
    train_ids, eval_ids = list(X.index[tr]), list(X.index[ev])
    adapter.declare_split(f"fold{k}", train_ids, eval_ids)
    X_train, y_train = adapter.take(X, train_ids), adapter.take(y, train_ids)
    if selector is None:
        selector = SelectKBest(f_classif, k=3).fit(X_train, y_train)
    clf = LogisticRegression().fit(selector.transform(X_train), y_train)
    adapter.write_predictions(
        f"fold{k}", eval_ids, clf.predict(selector.transform(adapter.take(X, eval_ids)))
    )
