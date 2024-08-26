from rdrf.forms.widgets.widgets import DurationWidgetHelper


def test_duration_compatibile_formats():
    helper = DurationWidgetHelper({})
    assert helper.compatible_formats("P0Y0M0D", "P0Y")
    assert helper.compatible_formats("P0Y0M0D", "P0Y0D")
    assert helper.compatible_formats("P0Y0M0D", "P0M0D")
    assert helper.compatible_formats("P0Y0M0DT0H0M0S", "PT0S")
    assert helper.compatible_formats("P0M0D", "P0D")


def test_duration_incompatible_formats():
    helper = DurationWidgetHelper({})
    assert not helper.compatible_formats("P0Y0M0D", "P0Y0M0DT0H0M0S")
    assert not helper.compatible_formats("P0Y0M0D", "P0Y0M0DT0M")
    assert not helper.compatible_formats("P0Y0M0D", "PT0M0H0S")
    assert not helper.compatible_formats("P0Y0M0DT0H0M", "PT0S")
    assert not helper.compatible_formats("P0M0D", "P0Y0D")
    assert not helper.compatible_formats("P0M0D", "PXTR")
    assert not helper.compatible_formats("ABCD", "XYZ")


def test_current_default_format():
    helper = DurationWidgetHelper(
        {
            "years": True,
            "months": False,
            "days": True,
            "hours": False,
            "minutes": False,
            "seconds": False,
        }
    )
    assert helper.current_format_default() == "P0Y0D"

    helper = DurationWidgetHelper({"weeks_only": True})
    assert helper.current_format_default() == "P0W"

    helper = DurationWidgetHelper(
        {
            "years": False,
            "months": False,
            "days": True,
            "hours": True,
            "minutes": True,
            "seconds": False,
        }
    )
    assert helper.current_format_default() == "P0DT0H0M"
