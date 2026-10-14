"""s04: grouped folds, but predictions are the training majority class; no classifier is fit."""

import numpy as np
from sklearn.model_selection import GroupKFold

from atlas import adapter

X, y = adapter.load_table()
groups = adapter.load_metadata().loc[X.index, "subject_id"]
for k, (tr, ev) in enumerate(GroupKFold(n_splits=4).split(X, y, groups)):
    train_ids, eval_ids = list(X.index[tr]), list(X.index[ev])
    adapter.declare_split(f"fold{k}", train_ids, eval_ids)
    majority = adapter.take(y, train_ids).mode().iloc[0]
    adapter.write_predictions(f"fold{k}", eval_ids, np.full(len(eval_ids), majority))
