"""s01 faulty (ATLAS-authored): supervised feature selection fit on every row, then a random-row split."""
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from atlas import adapter

X, y = adapter.load_table()
meta = adapter.load_metadata()
subject = meta['subject_id']
unique_subjects = subject.unique()
subject_kf = KFold(n_splits=4, shuffle=True, random_state=0)
for k, (train_subj_idx, eval_subj_idx) in enumerate(subject_kf.split(unique_subjects)):
    train_subjects = unique_subjects[train_subj_idx]
    eval_subjects = unique_subjects[eval_subj_idx]
    train_mask = subject.isin(train_subjects)
    eval_mask = subject.isin(eval_subjects)
    train_ids = list(X.index[train_mask])
    eval_ids = list(X.index[eval_mask])
    adapter.declare_split(f"fold{k}", train_ids, eval_ids)
    model = Pipeline([
        ("select", SelectKBest(f_classif, k=3)),
        ("scale", StandardScaler()),
        ("clf", LogisticRegression())
    ])
    model.fit(adapter.take(X, train_ids), adapter.take(y, train_ids))
    adapter.write_predictions(
        f"fold{k}",
        eval_ids,
        model.predict(adapter.take(X, eval_ids))
    )
