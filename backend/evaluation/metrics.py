"""
Evaluation metrics for ScamGuard AI
Measures performance on test dataset
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Results of evaluation"""
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    confusion_matrix: Dict[str, int]  # TP, TN, FP, FN
    avg_score_error: float
    correct_predictions: int
    total_predictions: int
    examples: List[Dict]


class ModelEvaluator:
    """Evaluates ScamGuard AI on test dataset"""
    
    def __init__(self, dataset_path: str = "data/test_dataset.json"):
        """
        Initialize evaluator
        
        Args:
            dataset_path: Path to test dataset JSON
        """
        self.dataset_path = Path(dataset_path)
        self.dataset = self._load_dataset()
        
    def _load_dataset(self) -> Dict:
        """Load test dataset"""
        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Dataset not found: {self.dataset_path}")
            return {"listings": []}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in dataset: {e}")
            return {"listings": []}
    
    def evaluate(self, predictions: List[Dict]) -> EvaluationResult:
        """
        Evaluate predictions against ground truth
        
        Args:
            predictions: List of predictions with format:
                {
                    "id": int,
                    "predicted_score": int,
                    "predicted_is_scam": bool
                }
        
        Returns:
            EvaluationResult with metrics
        """
        if not self.dataset.get("listings"):
            raise ValueError("Dataset is empty or not loaded")
        
        # Match predictions with ground truth
        results = []
        for pred in predictions:
            gt = next((l for l in self.dataset["listings"] if l["id"] == pred["id"]), None)
            if gt:
                results.append({
                    "id": pred["id"],
                    "predicted_score": pred["predicted_score"],
                    "predicted_is_scam": pred["predicted_is_scam"],
                    "actual_score": gt["ground_truth_score"],
                    "actual_is_scam": gt["is_scam"],
                    "score_error": abs(pred["predicted_score"] - gt["ground_truth_score"])
                })
        
        if not results:
            raise ValueError("No matching predictions found")
        
        # Calculate confusion matrix
        tp = sum(1 for r in results if r["predicted_is_scam"] and r["actual_is_scam"])
        tn = sum(1 for r in results if not r["predicted_is_scam"] and not r["actual_is_scam"])
        fp = sum(1 for r in results if r["predicted_is_scam"] and not r["actual_is_scam"])
        fn = sum(1 for r in results if not r["predicted_is_scam"] and r["actual_is_scam"])
        
        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / len(results) if results else 0.0
        
        # Average score error
        avg_error = sum(r["score_error"] for r in results) / len(results)
        
        # Count correct predictions (within 10 points)
        correct = sum(1 for r in results if r["score_error"] <= 10)
        
        return EvaluationResult(
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            confusion_matrix={
                "true_positive": tp,
                "true_negative": tn,
                "false_positive": fp,
                "false_negative": fn
            },
            avg_score_error=avg_error,
            correct_predictions=correct,
            total_predictions=len(results),
            examples=results[:10]  # First 10 examples
        )
    
    def get_dataset_summary(self) -> Dict:
        """Get summary of test dataset"""
        listings = self.dataset.get("listings", [])
        
        return {
            "total_samples": len(listings),
            "scam_samples": sum(1 for l in listings if l["is_scam"]),
            "safe_samples": sum(1 for l in listings if not l["is_scam"]),
            "avg_scam_score": sum(l["ground_truth_score"] for l in listings if l["is_scam"]) / max(1, sum(1 for l in listings if l["is_scam"])),
            "avg_safe_score": sum(l["ground_truth_score"] for l in listings if not l["is_scam"]) / max(1, sum(1 for l in listings if not l["is_scam"])),
            "categories": {
                "scam": sum(1 for l in listings if l.get("category") == "scam"),
                "suspicious": sum(1 for l in listings if l.get("category") == "suspicious"),
                "safe": sum(1 for l in listings if l.get("category") == "safe")
            }
        }


def calculate_metrics_simple(predictions: List[Tuple[int, bool]], 
                             ground_truth: List[Tuple[int, bool]]) -> Dict:
    """
    Simple metric calculation (for quick evaluation)
    
    Args:
        predictions: List of (score, is_scam) tuples
        ground_truth: List of (score, is_scam) tuples
    
    Returns:
        Dict with precision, recall, f1
    """
    if len(predictions) != len(ground_truth):
        raise ValueError("Predictions and ground truth must have same length")
    
    tp = sum(1 for (p_s, p_scam), (g_s, g_scam) in zip(predictions, ground_truth) 
             if p_scam and g_scam)
    tn = sum(1 for (p_s, p_scam), (g_s, g_scam) in zip(predictions, ground_truth) 
             if not p_scam and not g_scam)
    fp = sum(1 for (p_s, p_scam), (g_s, g_scam) in zip(predictions, ground_truth) 
             if p_scam and not g_scam)
    fn = sum(1 for (p_s, p_scam), (g_s, g_scam) in zip(predictions, ground_truth) 
             if not p_scam and g_scam)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1_score": round(f1, 3),
        "confusion_matrix": {"TP": tp, "TN": tn, "FP": fp, "FN": fn}
    }


# Example usage
if __name__ == "__main__":
    # Test with simple data
    evaluator = ModelEvaluator()
    
    # Print dataset summary
    summary = evaluator.get_dataset_summary()
    print("Dataset Summary:")
    print(f"  Total samples: {summary['total_samples']}")
    print(f"  Scam samples: {summary['scam_samples']}")
    print(f"  Safe samples: {summary['safe_samples']}")
    print(f"  Avg scam score: {summary['avg_scam_score']:.1f}")
    print(f"  Avg safe score: {summary['avg_safe_score']:.1f}")
    
    # Mock predictions (replace with actual model predictions)
    mock_predictions = [
        {"id": 1, "predicted_score": 90, "predicted_is_scam": True},
        {"id": 2, "predicted_score": 85, "predicted_is_scam": True},
        {"id": 16, "predicted_score": 15, "predicted_is_scam": False},
        {"id": 17, "predicted_score": 10, "predicted_is_scam": False},
    ]
    
    try:
        result = evaluator.evaluate(mock_predictions)
        print(f"\nEvaluation Results:")
        print(f"  Precision: {result.precision:.2%}")
        print(f"  Recall: {result.recall:.2%}")
        print(f"  F1 Score: {result.f1_score:.2%}")
        print(f"  Accuracy: {result.accuracy:.2%}")
        print(f"  Avg Score Error: {result.avg_score_error:.1f}")
    except ValueError as e:
        print(f"Evaluation error: {e}")
