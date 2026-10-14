"""s05b: one selector fit only on subjects that are in every fold's training set, then reused across folds."""

from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

from atlas import adapter

ALWAYS_TRAIN = {"S07", "S08"}  # never evaluated in this protocol

X, y = adapter.load_table()
subject = adapter.load_metadata().loc[X.index, "subject_id"]
fit_ids = list(X.index[subject.isin(ALWAYS_TRAIN)])
selector = SelectKBest(f_classif, k=3).fit(
    adapter.take(X, fit_ids), adapter.take(y, fit_ids)
)
rotating = X.index[~subject.isin(ALWAYS_TRAIN)]
for k, (_, ev) in enumerate(
    GroupKFold(n_splits=3).split(rotating, groups=subject.loc[rotating])
):
    eval_ids = list(rotating[ev])
    train_ids = [r for r in X.index if r not in set(eval_ids)]
    adapter.declare_split(f"fold{k}", train_ids, eval_ids)
    X_train, y_train = adapter.take(X, train_ids), adapter.take(y, train_ids)
    clf = LogisticRegression().fit(selector.transform(X_train), y_train)
    adapter.write_predictions(
        f"fold{k}", eval_ids, clf.predict(selector.transform(adapter.take(X, eval_ids)))
    )
