from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.metrics import confusion_matrix
import joblib

def train_models(X_train, y_train, X_test, y_test):

    print("Training models...")

    # 🔹 Classification Model
    clf = RandomForestClassifier(
    n_estimators=200,
    max_depth=20,
    min_samples_split=5,
    random_state=42,
    n_jobs=-1
    )
    clf.fit(X_train, y_train)

    # Predictions
    y_pred = clf.predict(X_test)

    print("\n📊 Classification Results:")
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print(classification_report(y_test, y_pred))

    # 🔹 Anomaly Model
    anomaly_model = IsolationForest(contamination=0.05, n_jobs=-1)
    anomaly_model.fit(X_train)

    anomaly_pred = anomaly_model.predict(X_test)

    print("\n🚨 Anomaly Detection Results:")
    print("Sample Predictions:", anomaly_pred[:20])
    print(confusion_matrix(y_test, y_pred))

    # Save models
    joblib.dump(anomaly_model, "backend/models/anomaly.pkl")
    joblib.dump(clf, "backend/models/classifier.pkl")

    print("Models saved successfully ✅")