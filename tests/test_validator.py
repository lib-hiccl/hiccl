"""Tests for hiccl.validator — Reactive FormValidator."""

from hiccl.validator import FormValidator, required, min_length, email


def test_form_validator_rules_and_signals():
    # 1. Initialize validator with custom rules
    validator = FormValidator(
        {
            "username": [required("Username required"), min_length(5, "Too short")],
            "email": [required(), email("Invalid email")],
        }
    )

    # Initial state should be valid as no errors have occurred yet
    assert validator.is_valid.get() is True
    assert validator.get_error("username") == ""

    # 2. Validate empty values
    data_empty = {"username": "", "email": ""}
    is_ok = validator.validate(data_empty)

    assert is_ok is False
    assert validator.is_valid.get() is False
    assert validator.get_error("username") == "Username required"
    assert validator.get_error("email") == "This field is required."

    # 3. Validate populated but invalid values
    data_invalid = {"username": "abc", "email": "john-at-example-dot-com"}
    is_ok2 = validator.validate(data_invalid)

    assert is_ok2 is False
    assert validator.is_valid.get() is False
    assert validator.get_error("username") == "Too short"
    assert validator.get_error("email") == "Invalid email"

    # 4. Validate fully correct values
    data_valid = {"username": "superdev", "email": "john@example.com"}
    is_ok3 = validator.validate(data_valid)

    assert is_ok3 is True
    assert validator.is_valid.get() is True
    assert validator.get_error("username") == ""
    assert validator.get_error("email") == ""
    assert validator.errors.get() == {}
