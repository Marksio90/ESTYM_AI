"""ML-based correction model for cost estimation.

Architecture: Parametric Baseline + ML Residual
- Parametric formulas provide baseline estimate (day-one ready)
- ML model (XGBoost/LightGBM) learns residuals: actual_time - parametric_estimate
- SHAP provides interpretability (which features drive the correction)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import structlog

logger = structlog.get_logger()

try:
    import xgboost as xgb

    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import shap

    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


# Feature vector schema for the ML model
FEATURE_NAMES = [
    "bend_count",
    "spot_weld_count",
    "linear_weld_length_mm",
    "hole_count",
    "thread_count",
    "material_thickness_mm",
    "overall_length_mm",
    "overall_width_mm",
    "weight_kg",
    "surface_area_m2",
    "batch_size",
    "material_form_encoded",  # ordinal: wire=0, tube=1, profile=2, sheet=3, bar=4, ...
    "weld_type_encoded",  # ordinal: none=0, spot=1, MIG=2, TIG=3, mixed=4
    "surface_finish_encoded",  # ordinal: raw=0, galvanized=1, painted=2, powder=3
]


@dataclass
class MLPrediction:
    """Result of ML correction."""
    parametric_estimate_sec: float
    ml_correction_sec: float
    corrected_estimate_sec: float
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    top_shap_features: list[dict] = None  # [{feature, value, shap_value}]
    model_version: str = ""

    def __post_init__(self):
        if self.top_shap_features is None:
            self.top_shap_features = []


def extract_feature_vector(spec, plan) -> np.ndarray:
    """Extract feature vector from PartSpec and TechPlan for ML model."""
    from ..models.enums import MaterialForm, SurfaceFinish, WeldingType

    mat_form_map = {
        MaterialForm.WIRE: 0, MaterialForm.TUBE: 1, MaterialForm.PROFILE: 2,
        MaterialForm.SHEET: 3, MaterialForm.BAR: 4, MaterialForm.FLATBAR: 5,
        MaterialForm.ANGLE: 6, MaterialForm.OTHER: 7,
    }
    weld_type_map = {
        WeldingType.NONE: 0, WeldingType.SPOT: 1, WeldingType.MIG: 2,
        WeldingType.TIG: 3, WeldingType.MIXED: 4, WeldingType.ROBOTIC: 5,
        WeldingType.UNKNOWN: 0,
    }
    finish_map = {
        SurfaceFinish.RAW: 0, SurfaceFinish.GALVANIZED: 1,
        SurfaceFinish.PAINTED: 2, SurfaceFinish.POWDER_COATED: 3,
        SurfaceFinish.UNKNOWN: 0, SurfaceFinish.OUTSOURCED: 4,
    }

    g = spec.geometry
    bend_count = 0
    if g.wire:
        bend_count += g.wire.bend_count
    if g.sheet:
        bend_count += g.sheet.bend_count
    if g.tube:
        bend_count += g.tube.bend_count

    thickness = 0.0
    mat_form = MaterialForm.OTHER
    if spec.materials:
        m = spec.materials[0]
        thickness = m.thickness_mm or m.diameter_mm or 0.0
        mat_form = m.form

    features = np.array([
        bend_count,
        g.welds.spot_weld_count,
        g.welds.linear_weld_length_mm,
        g.holes.count,
        g.holes.threaded_count,
        thickness,
        g.overall_length_mm or 0.0,
        g.overall_width_mm or 0.0,
        g.weight_kg or 0.0,
        g.surface_area_m2 or 0.0,
        plan.batch_size,
        mat_form_map.get(mat_form, 7),
        weld_type_map.get(g.welds.weld_type, 0),
        finish_map.get(spec.process_requirements.surface_finish, 0),
    ], dtype=np.float32)

    return features


class CostMLCorrector:
    """XGBoost-based residual correction model."""

    def __init__(self, model_path: str | Path | None = None):
        self.model: Optional[xgb.Booster] = None
        self.model_version = "none"
        self.explainer = None

        if model_path and HAS_XGB:
            self.load(model_path)

    def load(self, model_path: str | Path) -> bool:
        """Load a trained XGBoost model."""
        if not HAS_XGB:
            logger.warning("xgboost not installed, ML correction disabled")
            return False

        try:
            self.model = xgb.Booster()
            self.model.load_model(str(model_path))
            self.model_version = Path(model_path).stem
            logger.info("ml_model_loaded", path=str(model_path))

            if HAS_SHAP:
                self.explainer = shap.TreeExplainer(self.model)

            return True
        except Exception as e:
            logger.error("ml_model_load_failed", error=str(e))
            self.model = None
            return False

    def predict(
        self,
        feature_vector: np.ndarray,
        parametric_estimate_sec: float,
    ) -> MLPrediction:
        """
        Predict the residual correction and return corrected estimate.

        If no model is loaded, returns zero correction.
        """
        if self.model is None or not HAS_XGB:
            return MLPrediction(
                parametric_estimate_sec=parametric_estimate_sec,
                ml_correction_sec=0.0,
                corrected_estimate_sec=parametric_estimate_sec,
                model_version="none (parametric only)",
            )

        dmatrix = xgb.DMatrix(feature_vector.reshape(1, -1), feature_names=FEATURE_NAMES)
        residual = float(self.model.predict(dmatrix)[0])

        corrected = parametric_estimate_sec + residual

        # SHAP explanation
        top_features = []
        if self.explainer and HAS_SHAP:
            try:
                shap_values = self.explainer.shap_values(dmatrix)
                if shap_values is not None:
                    sv = shap_values[0] if len(shap_values.shape) > 1 else shap_values
                    indices = np.argsort(np.abs(sv))[::-1][:5]
                    for idx in indices:
                        top_features.append({
                            "feature": FEATURE_NAMES[idx],
                            "value": float(feature_vector[idx]),
                            "shap_value": float(sv[idx]),
                        })
            except Exception as e:
                logger.warning("shap_explanation_failed", error=str(e))

        return MLPrediction(
            parametric_estimate_sec=parametric_estimate_sec,
            ml_correction_sec=round(residual, 2),
            corrected_estimate_sec=round(max(corrected, 0), 2),
            top_shap_features=top_features,
            model_version=self.model_version,
        )

    @staticmethod
    def prepare_training_data(
        records: list[dict],
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data from historical production records.

        Each record should contain:
        - feature_vector: list[float] (14 values)
        - parametric_estimate_sec: float
        - actual_time_sec: float

        Returns (X, y) where y = actual - parametric (residual).
        """
        X = np.array([r["feature_vector"] for r in records], dtype=np.float32)
        y = np.array([
            r["actual_time_sec"] - r["parametric_estimate_sec"]
            for r in records
        ], dtype=np.float32)
        return X, y

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        params: dict | None = None,
        num_rounds: int = 200,
        save_path: str | Path | None = None,
    ) -> dict:
        """
        Train the XGBoost residual model.

        Returns training metrics.
        """
        if not HAS_XGB:
            return {"error": "xgboost not installed"}

        default_params = {
            "objective": "reg:squarederror",
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 5,
            "eval_metric": "mae",
        }
        if params:
            default_params.update(params)

        dtrain = xgb.DMatrix(X, label=y, feature_names=FEATURE_NAMES)
        eval_results: dict = {}
        self.model = xgb.train(
            default_params,
            dtrain,
            num_boost_round=num_rounds,
            evals=[(dtrain, "train")],
            evals_result=eval_results,
            verbose_eval=False,
        )

        if save_path:
            self.model.save_model(str(save_path))
            self.model_version = Path(save_path).stem
            logger.info("ml_model_saved", path=str(save_path))

        if HAS_SHAP:
            self.explainer = shap.TreeExplainer(self.model)

        final_mae = eval_results.get("train", {}).get("mae", [None])[-1]
        return {
            "trained_samples": X.shape[0],
            "num_features": X.shape[1],
            "final_train_mae": final_mae,
            "model_version": self.model_version,
        }
