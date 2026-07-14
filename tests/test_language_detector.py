from app.utils.detector import LanguageDetector


def test_detect_language_success():
    # Test supported extensions
    assert LanguageDetector.detect_language("main.py") == "Python"
    assert LanguageDetector.detect_language("script.JS") == "JavaScript"
    assert LanguageDetector.detect_language("component.tsx") == "TypeScript"
    assert LanguageDetector.detect_language("App.java") == "Java"
    assert LanguageDetector.detect_language("service.go") == "Go"
    assert LanguageDetector.detect_language("lib.rs") == "Rust"
    assert LanguageDetector.detect_language("Program.cs") == "C#"
    assert LanguageDetector.detect_language("main.cpp") == "C++"
    assert LanguageDetector.detect_language("header.h") == "C"


def test_detect_language_ignored_extensions():
    # Test binary/compiled extensions
    assert LanguageDetector.detect_language("image.png") is None
    assert LanguageDetector.detect_language("archive.zip") is None
    assert LanguageDetector.detect_language("executable.exe") is None
    assert LanguageDetector.detect_language("compiled.pyc") is None
    assert LanguageDetector.detect_language("library.so") is None


def test_detect_language_ignored_filenames():
    # Test package lock files
    assert LanguageDetector.detect_language("package-lock.json") is None
    assert LanguageDetector.detect_language("Yarn.lock") is None
    assert LanguageDetector.detect_language("Cargo.lock") is None


def test_detect_language_unsupported():
    # Test text or unknown scripts
    assert LanguageDetector.detect_language("readme.txt") is None
    assert LanguageDetector.detect_language("Makefile") is None
    assert LanguageDetector.detect_language("script.sh") is None
    assert LanguageDetector.detect_language("document.pdf") is None
    assert LanguageDetector.detect_language("no_extension") is None
    assert LanguageDetector.detect_language("") is None
