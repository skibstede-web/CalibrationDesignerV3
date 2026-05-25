def test_package_imports() -> None:
    import calibration_designer_v3

    assert calibration_designer_v3.__version__.startswith("0.")
