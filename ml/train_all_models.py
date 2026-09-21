from pathlib import Path

import joblib
from sklearn.datasets import load_breast_cancer, load_diabetes, load_digits, load_iris, load_wine
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

from model_registry import MODEL_DIR


MODEL_DIR.mkdir(exist_ok=True)


def train_classifier(name, dataset, estimator):
    features, targets = dataset.data, dataset.target
    train_features, test_features, train_targets, test_targets = train_test_split(
        features, targets, test_size=0.2, random_state=42, stratify=targets
    )
    estimator.fit(train_features, train_targets)
    accuracy = estimator.score(test_features, test_targets)
    joblib.dump(estimator, MODEL_DIR / f"{name}.pkl")
    print(f"{name}: saved ({accuracy:.3f} accuracy)")


def train_regression(name, dataset, estimator):
    train_features, test_features, train_targets, test_targets = train_test_split(
        dataset.data, dataset.target, test_size=0.2, random_state=42
    )
    estimator.fit(train_features, train_targets)
    score = estimator.score(test_features, test_targets)
    joblib.dump(estimator, MODEL_DIR / f"{name}.pkl")
    print(f"{name}: saved ({score:.3f} R2 score)")


train_classifier("breast_cancer", load_breast_cancer(), LogisticRegression(max_iter=5000))
train_classifier("iris", load_iris(), RandomForestClassifier(n_estimators=100, random_state=42))
train_classifier("wine", load_wine(), DecisionTreeClassifier(random_state=42))
train_regression("diabetes", load_diabetes(), LinearRegression())
train_classifier("digits", load_digits(), LogisticRegression(max_iter=1000))
print(f"Artifacts written to {MODEL_DIR}")
