"""s11a future_time label leak: training uses every day before the cutoff (ATLAS-authored flaw).

A training row's label is known 7 days after its prediction day, so the last 7 training days of
each fold have labels that are not yet available at the fold's cutoff.
"""

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from atlas import adapter

X, y = adapter.load_table()
day = adapter.load_metadata().loc[X.index, "pred_day"]
for k in range(4):
    cutoff = 60 + 15 * k
    train_ids = list(X.index[day < cutoff])
    eval_ids = list(X.index[(day >= cutoff) & (day < cutoff + 15)])
    adapter.declare_split(f"fold{k}", train_ids, eval_ids, training_cutoff=cutoff)
    model = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression())])
    model.fit(adapter.take(X, train_ids), adapter.take(y, train_ids))
    adapter.write_predictions(
        f"fold{k}", eval_ids, model.predict(adapter.take(X, eval_ids))
    )
