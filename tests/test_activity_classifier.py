from prism.intelligence.activity_classifier import (
    ActivityClassificationEngine,
)
from prism.intelligence.models.activity_classification_models import (
    ActivityCategory,
    ProgrammingLanguage,
)


def test_classify_java_class_creation() -> None:
    classifier = ActivityClassificationEngine()
    java_code = """
    package com.prism.billing;
    public class StripePaymentService implements PaymentService {
        @Override
        public void processPayment() {}
    }
    """
    res = classifier.classify(
        event_type="class_create",
        file_path="src/main/java/com/prism/billing/StripePaymentService.java",
        code_snippet=java_code,
    )
    assert res.category == ActivityCategory.CODING
    assert res.language == ProgrammingLanguage.JAVA.value
    assert res.concept == "Object-Oriented Programming"
    assert res.subconcept == "Class Definition"
    assert "Java" in (res.related_skill or "")
    assert res.project_component == "backend"
    assert res.confidence_score >= 0.90


def test_classify_react_component_creation() -> None:
    classifier = ActivityClassificationEngine()
    ts_code = """
    import React, { useState } from 'react';
    export const UserProfileModal = () => {
        const [open, setOpen] = useState(false);
        return <div className="modal">Profile</div>;
    };
    """
    res = classifier.classify(
        event_type="component_create",
        file_path="src/components/UserProfileModal.tsx",
        code_snippet=ts_code,
    )
    assert res.category == ActivityCategory.CODING
    assert res.language == ProgrammingLanguage.TYPESCRIPT.value
    assert res.framework == "React"
    assert res.concept == "Component Architecture"
    assert res.project_component == "frontend"
    assert res.confidence_score >= 0.90


def test_classify_testing_activity() -> None:
    classifier = ActivityClassificationEngine()
    res = classifier.classify(
        event_type="test_run",
        file_path="tests/test_auth.py",
        code_snippet="def test_login_success(): assert True",
    )
    assert res.category == ActivityCategory.TESTING
    assert res.language == ProgrammingLanguage.PYTHON.value
    assert res.concept == "Quality Assurance & Testing"
    assert res.project_component == "testing"


def test_classify_debugging_activity() -> None:
    classifier = ActivityClassificationEngine()
    res = classifier.classify(
        event_type="runtime_error",
        file_path="src/api/payment.py",
        code_snippet="ZeroDivisionError: division by zero",
    )
    assert res.category == ActivityCategory.DEBUGGING
    assert res.concept == "Error Diagnostics"


def test_classify_refactoring_activity() -> None:
    classifier = ActivityClassificationEngine()
    res = classifier.classify(
        event_type="refactor",
        file_path="src/services/billing.go",
        code_snippet="func RefactoredBillingEngine() {}",
    )
    assert res.category == ActivityCategory.REFACTORING
    assert res.language == ProgrammingLanguage.GO.value
    assert res.concept == "Software Architecture"
