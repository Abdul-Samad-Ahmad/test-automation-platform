import os
import pytest
import allure
from appium import webdriver
from appium.options.android import UiAutomator2Options

# 1. Register the custom command-line option
def pytest_addoption(parser):
    """
    Define a single CLI option: --apk
    """
    parser.addoption(
        "--apk",
        action="store",
        default=None,
        help="Path to the APK file under test",
    )

@pytest.fixture(scope="session")
def driver(request):
    """Appium driver fixture with APK path passed via --apk."""
    # Get APK path from CLI
    apk_path = request.config.getoption("--apk")

    if not apk_path:
        pytest.fail("No APK path provided! Backend must call pytest with --apk=/path/to/app.apk")

    if not os.path.exists(apk_path):
        pytest.fail(f"APK file not found at: {apk_path}")

    print(f"Initializing Appium with APK: {apk_path}")

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = "AndroidDevice"
    options.no_reset = False
    options.full_reset = True
    options.auto_grant_permissions = False
    options.dont_stop_app_on_reset = True
    options.app = apk_path   # ✅ use the same --apk value

    # TODO: adjust URL / capabilities to your setup
    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

    yield driver

    driver.quit()

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Add Allure attachments on test failure"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        driver = item.funcargs.get('driver')
        if driver:
            try:
                screenshot = driver.get_screenshot_as_png()
                allure.attach(
                    screenshot,
                    name="Failure Screenshot",
                    attachment_type=allure.attachment_type.PNG
                )
            except Exception as e:
                print(f"Failed to capture screenshot: {str(e)}")
 