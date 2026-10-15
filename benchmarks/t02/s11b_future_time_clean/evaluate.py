"""s11b future_time clean: training rows' labels are known by each fold's cutoff.

A row's label is known 7 days after its prediction day (horizon 5 + reporting delay 2), so only
days with day + 7 <= cutoff train; evaluation starts at the cutoff (gap 0).
"""

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from atlas import adapter

LABEL_DELAY = 7

X, y = adapter.load_table()
day = adapter.load_metadata().loc[X.index, "pred_day"]
for k in range(4):
    cutoff = 60 + 15 * k
    train_ids = list(X.index[day + LABEL_DELAY <= cutoff])
    eval_ids = list(X.index[(day >= cutoff) & (day < cutoff + 15)])
    adapter.declare_split(f"fold{k}", train_ids, eval_ids, training_cutoff=cutoff)
    model = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression())])
    model.fit(adapter.take(X, train_ids), adapter.take(y, train_ids))
    adapter.write_predictions(
        f"fold{k}", eval_ids, model.predict(adapter.take(X, eval_ids))
    )
