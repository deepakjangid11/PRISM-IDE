from prism.intelligence.languages.registry import language_registry
from prism.intelligence.models.activity_classification_models import (
    ProgrammingLanguage,
)


def test_language_detection_by_extension() -> None:
    cases = [
        ("app/main.py", ProgrammingLanguage.PYTHON.value),
        ("frontend/index.tsx", ProgrammingLanguage.TYPESCRIPT.value),
        ("frontend/utils.js", ProgrammingLanguage.JAVASCRIPT.value),
        ("backend/OrderService.java", ProgrammingLanguage.JAVA.value),
        ("backend/Program.cs", ProgrammingLanguage.CSHARP.value),
        ("cmd/server.go", ProgrammingLanguage.GO.value),
        ("src/lib.rs", ProgrammingLanguage.RUST.value),
        ("native/engine.cpp", ProgrammingLanguage.CPP.value),
        ("native/driver.c", ProgrammingLanguage.C.value),
        ("web/index.php", ProgrammingLanguage.PHP.value),
        ("app/models/user.rb", ProgrammingLanguage.RUBY.value),
        ("android/MainActivity.kt", ProgrammingLanguage.KOTLIN.value),
        ("ios/ContentView.swift", ProgrammingLanguage.SWIFT.value),
        ("mobile/lib/main.dart", ProgrammingLanguage.DART.value),
        ("db/schema.sql", ProgrammingLanguage.SQL.value),
        ("public/index.html", ProgrammingLanguage.HTML.value),
        ("public/styles.css", ProgrammingLanguage.CSS.value),
        ("analysis/stats.r", ProgrammingLanguage.R.value),
        ("science/calc.jl", ProgrammingLanguage.JULIA.value),
    ]
    for path, expected_lang in cases:
        assert language_registry.detect_language(path) == expected_lang


def test_language_detection_by_shebang() -> None:
    py_code = "#!/usr/bin/env python3\nprint('hello')"
    assert (
        language_registry.detect_language("script", py_code)
        == ProgrammingLanguage.PYTHON.value
    )

    node_code = "#!/usr/bin/env node\nconsole.log('hi')"
    assert (
        language_registry.detect_language("runner", node_code)
        == ProgrammingLanguage.JAVASCRIPT.value
    )


def test_language_detection_by_content_heuristics() -> None:
    java_code = "package com.example.service;\npublic class OrderService {}"
    assert (
        language_registry.detect_language("unknown_file", java_code)
        == ProgrammingLanguage.JAVA.value
    )

    go_code = "func calculateTotal(a int, b int) int { return a + b }"
    assert (
        language_registry.detect_language("unknown_file", go_code)
        == ProgrammingLanguage.GO.value
    )

    rust_code = "pub fn execute_command(cmd: &str) -> Result<(), Error> {}"
    assert (
        language_registry.detect_language("unknown_file", rust_code)
        == ProgrammingLanguage.RUST.value
    )

    sql_code = "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));"
    assert (
        language_registry.detect_language("unknown_file", sql_code)
        == ProgrammingLanguage.SQL.value
    )


def test_framework_detection_across_languages() -> None:
    py_fastapi = "from fastapi import FastAPI, APIRouter\napp = FastAPI()"
    py_adapter = language_registry.get_adapter_for_file("main.py")
    assert "FastAPI" in py_adapter.detect_frameworks(py_fastapi)

    ts_react = (
        "import React, { useState } from 'react';\nexport const Card = () => <div/>;"
    )
    ts_adapter = language_registry.get_adapter_for_file("Card.tsx")
    assert "React" in ts_adapter.detect_frameworks(ts_react)

    java_spring = "@RestController\n@SpringBootApplication\npublic class App {}"
    java_adapter = language_registry.get_adapter_for_file("App.java")
    assert "Spring Boot" in java_adapter.detect_frameworks(java_spring)

    go_gin = 'import "github.com/gin-gonic/gin"\nr := gin.Default()'
    go_adapter = language_registry.get_adapter_for_file("main.go")
    assert "Gin" in go_adapter.detect_frameworks(go_gin)

    rust_tokio = "#[tokio::main]\nasync fn main() {}"
    rust_adapter = language_registry.get_adapter_for_file("main.rs")
    assert "Tokio" in rust_adapter.detect_frameworks(rust_tokio)

    dart_flutter = (
        "import 'package:flutter/material.dart';\nclass Home extends StatelessWidget {}"
    )
    dart_adapter = language_registry.get_adapter_for_file("home.dart")
    assert "Flutter" in dart_adapter.detect_frameworks(dart_flutter)


def test_concept_extraction_across_languages() -> None:
    # Java Interface
    java_code = "public interface PaymentProcessor {\n    void process();\n}"
    java_adapter = language_registry.get_adapter_for_file("PaymentProcessor.java")
    java_concepts = [c.concept for c in java_adapter.extract_concepts(java_code)]
    assert "Object-Oriented Programming" in java_concepts

    # Go Goroutines
    go_code = "go worker(jobs, results)\nselect { case <-done: return }"
    go_adapter = language_registry.get_adapter_for_file("worker.go")
    go_concepts = [c.concept for c in go_adapter.extract_concepts(go_code)]
    assert "Concurrency" in go_concepts

    # Rust Borrowing / Lifetimes
    rust_code = "let r = &mut buffer;\ntrait Summarizable { fn summarize(&self); }"
    rust_adapter = language_registry.get_adapter_for_file("lib.rs")
    rust_concepts = [c.concept for c in rust_adapter.extract_concepts(rust_code)]
    assert "Memory Safety" in rust_concepts or "Type Systems" in rust_concepts

    # SQL Joins & Transactions
    sql_code = (
        "SELECT * FROM orders INNER JOIN users ON orders.user_id = users.id; COMMIT;"
    )
    sql_adapter = language_registry.get_adapter_for_file("query.sql")
    sql_concepts = [c.concept for c in sql_adapter.extract_concepts(sql_code)]
    assert "Database Querying" in sql_concepts or "Transactions & ACID" in sql_concepts


def test_unsupported_language_graceful_fallback() -> None:
    adapter = language_registry.get_adapter_for_file("binary.bin", "raw binary data")
    assert adapter.language == ProgrammingLanguage.UNKNOWN.value
    result = adapter.analyze_code("some unknown code", "binary.bin")
    assert result.language == ProgrammingLanguage.UNKNOWN.value
    assert len(result.concepts) >= 1
    assert result.complexity in ("low", "medium", "high")
