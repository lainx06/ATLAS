"""s12b same_population blocked windows: contiguous evaluation blocks with purged neighbours.

Fold k evaluates windows 6k..6k+5 of every stream. Window j spans [5j, 5j + 10), so training
keeps only windows at least 5 samples away on either side: j <= 6k - 3 or j >= 6k + 8.
"""

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from atlas import adapter

X, y = adapter.load_table()
j = adapter.load_metadata().loc[X.index, "window_index"]
for k in range(4):
    first, last = 6 * k, 6 * k + 5
    eval_ids = list(X.index[(j >= first) & (j <= last)])
    train_ids = list(X.index[(j <= first - 3) | (j >= last + 3)])
    adapter.declare_split(f"fold{k}", train_ids, eval_ids)
    model = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression())])
    model.fit(adapter.take(X, train_ids), adapter.take(y, train_ids))
    adapter.write_predictions(
        f"fold{k}", eval_ids, model.predict(adapter.take(X, eval_ids))
    )
