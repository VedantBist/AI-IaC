from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
import joblib


# 1. Load dataset
data = load_breast_cancer()

X = data.data
y = data.target


# 2. Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


# 3. Create and train model
model = LogisticRegression(max_iter=5000)

model.fit(X_train, y_train)


# 4. Make predictions
y_pred = model.predict(X_test)


# 5. Evaluate model
accuracy = accuracy_score(y_test, y_pred)

print("Model Training Completed")
print("------------------------")
print(f"Accuracy: {accuracy:.4f}")

print("\nClassification Report:")
print(classification_report(
    y_test,
    y_pred,
    target_names=data.target_names
))


# 6. Save trained model
joblib.dump(model, "model.pkl")

print("\nModel saved successfully as model.pkl")