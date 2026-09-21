from pathlib import Path


MODEL_DIR = Path(__file__).resolve().parent / "models"

MODEL_REGISTRY = {
    "breast_cancer": {
        "model_id": "breast_cancer",
        "display_name": "Breast Cancer Classifier",
        "dataset": "Scikit-learn Breast Cancer Dataset",
        "task": "Binary Classification",
        "algorithm": "Logistic Regression",
        "features": 30,
        "output": "Malignant / Benign",
        "artifact": MODEL_DIR / "breast_cancer.pkl",
        "description": "Classifies a sample as malignant or benign.",
        "feature_names": [],
        "sample": [
            17.99, 10.38, 122.8, 1001.0, 0.1184, 0.2776, 0.3001,
            0.1471, 0.2419, 0.07871, 1.095, 0.9053, 8.589, 153.4,
            0.006399, 0.04904, 0.05373, 0.01587, 0.03003, 0.006193,
            25.38, 17.33, 184.6, 2019.0, 0.1622, 0.6656, 0.7119,
            0.2654, 0.4601, 0.1189,
        ],
        "labels": ["Malignant", "Benign"],
    },
    "iris": {
        "model_id": "iris",
        "display_name": "Iris Classifier",
        "dataset": "Scikit-learn Iris Dataset",
        "task": "Multiclass Classification",
        "algorithm": "Random Forest",
        "features": 4,
        "output": "Setosa / Versicolor / Virginica",
        "artifact": MODEL_DIR / "iris.pkl",
        "description": "Identifies the species of an iris flower.",
        "feature_names": ["Sepal length", "Sepal width", "Petal length", "Petal width"],
        "sample": [5.1, 3.5, 1.4, 0.2],
        "labels": ["Setosa", "Versicolor", "Virginica"],
    },
    "wine": {
        "model_id": "wine",
        "display_name": "Wine Classifier",
        "dataset": "Scikit-learn Wine Dataset",
        "task": "Multiclass Classification",
        "algorithm": "Decision Tree",
        "features": 13,
        "output": "Wine class labels",
        "artifact": MODEL_DIR / "wine.pkl",
        "description": "Classifies the cultivar of a wine sample.",
        "feature_names": ["Alcohol", "Malic acid", "Ash", "Alcalinity", "Magnesium", "Phenols", "Flavanoids", "Nonflavanoid phenols", "Proanthocyanins", "Color intensity", "Hue", "OD280/OD315", "Proline"],
        "sample": [14.23, 1.71, 2.43, 15.6, 127.0, 2.8, 3.06, 0.28, 2.29, 5.64, 1.04, 3.92, 1065.0],
        "labels": ["Class 0", "Class 1", "Class 2"],
    },
    "diabetes": {
        "model_id": "diabetes",
        "display_name": "Diabetes Predictor",
        "dataset": "Scikit-learn Diabetes Dataset",
        "task": "Regression",
        "algorithm": "Linear Regression",
        "features": 10,
        "output": "Numeric disease progression",
        "artifact": MODEL_DIR / "diabetes.pkl",
        "description": "Predicts a numeric diabetes progression measure.",
        "feature_names": ["Age", "Sex", "BMI", "Blood pressure", "S1", "S2", "S3", "S4", "S5", "S6"],
        "sample": [0.038, 0.05, 0.061, 0.021, -0.044, -0.034, -0.043, -0.003, 0.019, -0.017],
        "labels": [],
    },
    "digits": {
        "model_id": "digits",
        "display_name": "Handwritten Digit Classifier",
        "dataset": "Scikit-learn Digits Dataset",
        "task": "Multiclass Classification",
        "algorithm": "Logistic Regression",
        "features": 64,
        "output": "Digits 0-9",
        "artifact": MODEL_DIR / "digits.pkl",
        "description": "Recognizes a handwritten digit from 64 pixel features.",
        "feature_names": [],
        "sample": [0, 0, 5, 13, 9, 1, 0, 0, 0, 0, 13, 15, 10, 15, 5, 0, 0, 3, 15, 2, 0, 11, 8, 0, 0, 4, 12, 0, 0, 8, 8, 0, 0, 5, 8, 0, 0, 9, 8, 0, 0, 4, 11, 0, 1, 12, 7, 0, 0, 2, 14, 5, 10, 12, 0, 0, 0, 0, 6, 13, 10, 0, 0, 0],
        "labels": [str(value) for value in range(10)],
    },
}


def public_model_metadata():
    return [
        {
            key: value
            for key, value in metadata.items()
            if key != "artifact"
        }
        for metadata in MODEL_REGISTRY.values()
    ]
