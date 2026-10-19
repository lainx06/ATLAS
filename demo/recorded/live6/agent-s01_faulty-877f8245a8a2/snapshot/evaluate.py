"""s01 faulty (ATLAS-authored): supervised feature selection fit on every row, then a random-row split."""

from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from atlas import adapter

X, y = adapter.load_table()
# Global: the selector learns from every row's label, including future evaluation rows.
X_selected = SelectKBest(f_classif, k=3).fit_transform(X, y)
for k, (tr, ev) in enumerate(
    KFold(n_splits=4, shuffle=True, random_state=0).split(X_selected)
):
    train_ids, eval_ids = list(X.index[tr]), list(X.index[ev])
    adapter.declare_split(f"fold{k}", train_ids, eval_ids)
    model = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression())])
    model.fit(adapter.take(X_selected, train_ids), adapter.take(y, train_ids))
    adapter.write_predictions(
        f"fold{k}", eval_ids, model.predict(adapter.take(X_selected, eval_ids))
    )
