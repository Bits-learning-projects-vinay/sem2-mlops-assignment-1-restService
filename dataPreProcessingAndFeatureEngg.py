import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from dataSetLoad import DataSetLoader


class HeartDiseaseCleaner(BaseEstimator, TransformerMixin):
    """
    Sklearn-compatible cleaner.
    FIX: The __init__ must only assign arguments. Modification (like list())
    must happen in transform to prevent RuntimeError during cross-validation.
    """

    def __init__(self, categorical_features=None):
        self.categorical_features = categorical_features

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)

        cleaned = X.copy()
        cleaned = cleaned.replace("?", pd.NA)

        # Handle feature list conversion here, not in __init__
        cat_cols = list(self.categorical_features) if self.categorical_features else []

        present_categorical = [c for c in cat_cols if c in cleaned.columns]
        for col in present_categorical:
            mode = cleaned[col].mode(dropna=True)
            if not mode.empty:
                cleaned[col] = cleaned[col].fillna(mode.iloc[0])

        # Convert to numeric and handle any remaining NaNs with median
        cleaned = cleaned.apply(pd.to_numeric, errors="coerce")
        cleaned = cleaned.fillna(cleaned.median(numeric_only=True))
        return cleaned


class DataPreProcessingAndFeatureEngg:
    NUMERIC_FEATURES = ["age", "trestbps", "chol", "thalach", "oldpeak"]
    CATEGORICAL_FEATURES = [
        "sex",
        "cp",
        "fbs",
        "restecg",
        "exang",
        "slope",
        "ca",
        "thal",
    ]

    def __init__(self, dataset_id: int = 45):
        loader = DataSetLoader(dataset_id=dataset_id)
        self.features_before_clean = loader.get_features().copy()
        self.targets_before_clean = loader.get_targets().copy()

        # Internal state for cleaned data
        self.features = self.features_before_clean.copy()
        self.targets = self.targets_before_clean.copy()

    def before_clean_data(self):
        """Returns raw features and targets."""
        return self.features_before_clean, self.targets_before_clean

    def _clean_targets(self, targets_df: pd.DataFrame) -> pd.DataFrame:
        """Converts UCI multi-class targets (0-4) to binary (0/1)."""
        cleaned_targets = targets_df.copy()
        target_col = cleaned_targets.columns[0]
        cleaned_targets[target_col] = (
            pd.to_numeric(cleaned_targets[target_col], errors="coerce").fillna(0) > 0
        ).astype(int)
        return cleaned_targets

    def clean_data(self):
        """Vectorized cleaning of features and targets."""
        cleaner = HeartDiseaseCleaner(categorical_features=self.CATEGORICAL_FEATURES)
        self.features = cleaner.transform(self.features_before_clean)
        self.targets = self._clean_targets(self.targets_before_clean)
        return self.features, self.targets

    def get_binary_target(self):
        """Returns 0/1 target from raw data."""
        return self._clean_targets(self.targets_before_clean)

    def run_visual_eda(self, X, y):
        """Professional visualizations for assignment requirements."""
        df = pd.concat([X, y], axis=1)
        target_name = y.columns[0]

        sns.set_theme(style="whitegrid")
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        # 1. Class Balance
        sns.countplot(data=df, x=target_name, ax=axes[0], palette="viridis")
        axes[0].set_title("Target Distribution (0=Healthy, 1=Disease)")

        # 2. Age Distribution
        if "age" in df.columns:
            sns.histplot(
                data=df, x="age", hue=target_name, kde=True, ax=axes[1], element="step"
            )
            axes[1].set_title("Age Distribution by Risk")

        # 3. Correlation
        corr = df.corr(numeric_only=True)
        sns.heatmap(corr, annot=False, cmap="RdBu_r", center=0, ax=axes[2])
        axes[2].set_title("Feature Correlation Heatmap")

        plt.tight_layout()
        plt.show()

    def build_preprocessing_pipeline(self):
        """Creates an automated pipeline for numeric scaling and categorical encoding."""
        # Use simple presence checks to avoid errors if some columns are missing
        num_cols = [
            c for c in self.NUMERIC_FEATURES if c in self.features_before_clean.columns
        ]
        cat_cols = [
            c
            for c in self.CATEGORICAL_FEATURES
            if c in self.features_before_clean.columns
        ]

        numeric_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="mean")),
                ("scaler", StandardScaler()),
            ]
        )

        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            ]
        )

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, num_cols),
                ("cat", categorical_transformer, cat_cols),
            ]
        )
        return preprocessor

    def build_reproducible_preprocessing_pipeline(self):
        """
        Combines custom cleaning and standard preprocessing into one object.
        This is what ensures Task 4 'Reproducibility' requirements.
        """
        base_preprocessor = self.build_preprocessing_pipeline()
        return Pipeline(
            steps=[
                (
                    "cleaner",
                    HeartDiseaseCleaner(categorical_features=self.CATEGORICAL_FEATURES),
                ),
                ("preprocessor", base_preprocessor),
            ]
        )

    def get_processed_data(self):
        """Convenience method for main execution."""
        return self.clean_data()


if __name__ == "__main__":
    # Test script
    dp = DataPreProcessingAndFeatureEngg()
    X, y = dp.get_processed_data()
    print(f"Cleaned Data Shape: {X.shape}")
    dp.run_visual_eda(X, y)
