import pytest

import app.ai.agent.medicine_database as medicine_database
import app.services.disease_service as disease_service
from app.ai.classifier import yolo_classifier
from app.ai.classifier.common import ModelNotFoundError, pretty_name


class FakeResponse:
    def __init__(self, text):
        self.text = text


# ---------------------------------------------------------------- names

@pytest.mark.parametrize("folder,expected", [
    ("Tomato_Early_blight", "Tomato Early Blight"),
    ("Potato___Late_blight", "Potato Late Blight"),
    ("Tomato_healthy", "Tomato Healthy"),
    ("Apple___Cedar_apple_rust", "Apple Cedar Apple Rust"),
    ("Corn_(maize)___Common_rust_", "Corn (maize) Common Rust"),
])
def test_pretty_name(folder, expected):
    assert pretty_name(folder) == expected


# ---------------------------------------------------------------- selection

def stub_yolo(monkeypatch, result=None, missing=False):
    def predict(path):
        if missing:
            raise ModelNotFoundError("no yolo weights")
        return result

    monkeypatch.setattr(yolo_classifier, "predict_disease", predict)


def stub_efficientnet(monkeypatch, result):
    import sys
    import types

    module = types.ModuleType("app.ai.classifier.efficientnet_classifier")
    module.predict_disease = lambda path: result

    monkeypatch.setitem(
        sys.modules, "app.ai.classifier.efficientnet_classifier", module
    )


def test_yolo_is_the_default_backend(monkeypatch):
    monkeypatch.delenv("DISEASE_MODEL", raising=False)
    stub_yolo(monkeypatch, {"disease": "Tomato Late Blight", "confidence": 97.0, "model": "yolov8-cls"})
    stub_efficientnet(monkeypatch, {"disease": "WRONG", "confidence": 1, "model": "x"})

    result = disease_service.predict_disease("leaf.jpg")[0]

    assert result["disease"] == "Tomato Late Blight"
    assert result["model"] == "yolov8-cls"
    assert "mancozeb" in result["treatment"].lower()


def test_falls_back_to_efficientnet_without_yolo_weights(monkeypatch):
    monkeypatch.setenv("DISEASE_MODEL", "yolo")
    stub_yolo(monkeypatch, missing=True)
    stub_efficientnet(monkeypatch, {"disease": "Potato Healthy", "confidence": 95.0, "model": "efficientnet-b0"})

    result = disease_service.predict_disease("leaf.jpg")[0]

    assert result["disease"] == "Potato Healthy"
    assert result["model"] == "efficientnet-b0"


def test_efficientnet_can_be_forced(monkeypatch):
    monkeypatch.setenv("DISEASE_MODEL", "efficientnet")

    def must_not_run(path):
        raise AssertionError("YOLO must not be used")

    monkeypatch.setattr(yolo_classifier, "predict_disease", must_not_run)
    stub_efficientnet(monkeypatch, {"disease": "Tomato Healthy", "confidence": 99.0, "model": "efficientnet-b0"})

    assert disease_service.predict_disease("leaf.jpg")[0]["model"] == "efficientnet-b0"


def test_no_weights_at_all_raises_for_the_route_to_handle(monkeypatch):
    monkeypatch.setenv("DISEASE_MODEL", "yolo")
    stub_yolo(monkeypatch, missing=True)

    import sys
    import types

    module = types.ModuleType("app.ai.classifier.efficientnet_classifier")

    def missing(path):
        raise ModelNotFoundError("no efficientnet weights")

    module.predict_disease = missing
    monkeypatch.setitem(sys.modules, "app.ai.classifier.efficientnet_classifier", module)

    with pytest.raises(ModelNotFoundError):
        disease_service.predict_disease("leaf.jpg")


def test_uncertain_result_asks_for_a_clearer_photo(monkeypatch):
    stub_yolo(monkeypatch, {"disease": "Uncertain", "confidence": 61.2, "model": "yolov8-cls"})

    result = disease_service.predict_disease("leaf.jpg")[0]

    assert result["disease"] == "Uncertain prediction"
    assert "clearer" in result["treatment"]


# ---------------------------------------------------------------- new crops

def test_unknown_disease_gets_generated_advice_and_is_cached(monkeypatch):
    calls = {"count": 0}

    def fake_generate(prompt):
        calls["count"] += 1
        return FakeResponse('{"medicine": "Captan 50 WP", "cost": "Rs 400 per acre"}')

    import app.ai.gemini_client as gemini_client

    monkeypatch.setattr(gemini_client, "generate_content", fake_generate)
    medicine_database._generated.clear()

    stub_yolo(monkeypatch, {"disease": "Apple Scab", "confidence": 96.0, "model": "yolov8-cls"})

    first = disease_service.predict_disease("leaf.jpg")[0]
    second = disease_service.predict_disease("leaf.jpg")[0]

    assert "Captan" in first["treatment"]
    assert "local agriculture officer" in first["treatment"]
    assert calls["count"] == 1                 # second lookup came from the cache
    assert first["treatment"] == second["treatment"]


def test_gemini_failure_falls_back_to_expert_advice(monkeypatch):
    import app.ai.gemini_client as gemini_client

    def boom(prompt):
        raise RuntimeError("Gemini down")

    monkeypatch.setattr(gemini_client, "generate_content", boom)
    medicine_database._generated.clear()

    stub_yolo(monkeypatch, {"disease": "Grape Black Rot", "confidence": 93.0, "model": "yolov8-cls"})

    result = disease_service.predict_disease("leaf.jpg")[0]

    assert result["treatment"] == "Consult agricultural expert"


def test_known_diseases_never_call_gemini(monkeypatch):
    import app.ai.gemini_client as gemini_client

    def boom(prompt):
        raise AssertionError("Gemini must not be called for known diseases")

    monkeypatch.setattr(gemini_client, "generate_content", boom)

    assert medicine_database.get_medicine_info("Tomato Late Blight")["medicine"] == "Mancozeb 75% WP"


# ---------------------------------------------------------------- yolo wrapper

def test_yolo_wrapper_applies_the_confidence_threshold(monkeypatch):
    class Probs:
        def __init__(self, top1, conf):
            self.top1, self.top1conf = top1, conf

    class Result:
        def __init__(self, probs):
            self.probs = probs

    class FakeModel:
        names = {0: "Tomato_Early_blight", 1: "Potato___healthy"}

        def __init__(self, conf):
            self.conf = conf

        def predict(self, path, verbose=False):
            return [Result(Probs(1, self.conf))]

    monkeypatch.setattr(yolo_classifier, "CONFIDENCE_THRESHOLD", 90.0)

    monkeypatch.setattr(yolo_classifier, "_model", FakeModel(0.97))
    sure = yolo_classifier.predict_disease("leaf.jpg")
    assert sure == {"disease": "Potato Healthy", "confidence": 97.0, "model": "yolov8-cls"}

    monkeypatch.setattr(yolo_classifier, "_model", FakeModel(0.55))
    unsure = yolo_classifier.predict_disease("leaf.jpg")
    assert unsure["disease"] == "Uncertain"


def test_yolo_wrapper_reports_missing_weights(monkeypatch):
    monkeypatch.setattr(yolo_classifier, "_model", None)
    monkeypatch.setattr(yolo_classifier, "MODEL_PATH", "definitely/missing.pt")

    with pytest.raises(ModelNotFoundError):
        yolo_classifier.predict_disease("leaf.jpg")
