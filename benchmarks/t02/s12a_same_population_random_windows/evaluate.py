"""s12a same_population random windows: shuffled KFold over overlapping windows (ATLAS-authored flaw).

Neighbouring windows share samples, so random folds put overlapping windows of the same stream in
training and evaluation, closer than the declared 5-sample separation.
"""

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from atlas import adapter

X, y = adapter.load_table()
for k, (tr, ev) in enumerate(KFold(n_splits=4, shuffle=True, random_state=0).split(X)):
    train_ids, eval_ids = list(X.index[tr]), list(X.index[ev])
    adapter.declare_split(f"fold{k}", train_ids, eval_ids)
    model = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression())])
    model.fit(adapter.take(X, train_ids), adapter.take(y, train_ids))
    adapter.write_predictions(
        f"fold{k}", eval_ids, model.predict(adapter.take(X, eval_ids))
    )
