# import os
# import pytest
# import subprocess
# from utils.ai_agent import AIAgent
# from dotenv import load_dotenv

# load_dotenv()
# def run_tests_and_get_suggestions():
#     """
#     Main function to execute tests, and if they pass,
#     invoke the AI agent to suggest new test flows.
#     """
#     # Create necessary directories
#     os.makedirs("allure-results", exist_ok=True)
#     os.makedirs("screenshots", exist_ok=True)
#     os.makedirs("test-flows", exist_ok=True)

#     # Define paths
#     test_files = [
#         "tests/test_login_pytest.py",
#         "tests/test_onboarding_pytest.py"
#     ]    
#     allure_dir = "allure-results"
    
#     # Run pytest with Allure options
#     result = pytest.main([
#         *test_files,
#         f"--alluredir={allure_dir}",
#         "--clean-alluredir",
#         "-v",
#         "-n=4"
#     ])

#     # If tests passed, run the AI agent
#     if result == pytest.ExitCode.OK:
#         print("\n" + "="*80)
#         print("✅ All tests passed. Asking AI for new test case suggestions...")
#         print("="*80 + "\n")

#         # Ensure you have your OpenAI API key in an environment variable
#         api_key = os.getenv("OPENAI_API_KEY")
#         if not api_key:
#             print("🛑 Error: OPENAI_API_KEY environment variable not set.")
#             return

#         ai_agent = AIAgent(key=api_key)
        
#         flow_file = "test-flows/login_flow_success.json"
        
#         suggestions = ai_agent.suggest_new_tests(flow_file, test_files)
        
#         print("🤖 AI-Generated Test Suggestions:\n")
#         print(suggestions)
        
#         # Optionally, save suggestions to a file
#         with open("ai_test_suggestions.md", "w") as f:
#             f.write(suggestions)
#         print(f"\n💡 Suggestions also saved to 'ai_test_suggestions.md'")

#     else:
#         print("\n" + "="*80)
#         print("❌ Tests failed. Skipping AI suggestion step.")
#         print("="*80 + "\n")
        
#     # To view the report, run: allure serve allure-results
#     print(f"\nTo view the detailed test report, run: allure serve {allure_dir}")

# if __name__ == "__main__":
#     run_tests_and_get_suggestions()
import os
import shutil
# Disable auto-loading of 3rd-party pytest plugins (like browserstack)
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

import pytest
import allure_pytest  # pip install allure-pytest
import requests
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def send_module_status(module: str, status: str, message: str = ""):
    """Notify backend which module is running/completed."""
    try:
        requests.post(
            f"{BACKEND_URL}/api/module-status",
            json={"module": module, "status": status, "message": message},
            timeout=3,
        )
    except Exception:
        # Do not break tests if backend is down
        pass

def run_tests_and_get_suggestions(apk_path: str):
    print(f"[test_runner] Running tests for APK: {apk_path}")

    if not os.path.exists(apk_path):
        print(f"❌ Error: APK not found at {apk_path}")
        return

    project_root = os.path.dirname(os.path.dirname(__file__))
    os.chdir(project_root)

    # Allure results under tests/
    allure_dir = os.path.join("tests", "allure-results")
    if os.path.exists(allure_dir):
        shutil.rmtree(allure_dir)
    os.makedirs(allure_dir, exist_ok=True)

    # Tell allure-pytest where to write results (no --alluredir needed)
    os.environ["ALLURE_RESULTS_DIR"] = os.path.abspath(allure_dir)

    os.makedirs("screenshots", exist_ok=True)

    overall_ok = True

    # ---------- Login module ----------
    send_module_status("Login", "running", "Starting Login tests")

    result_login = pytest.main(
        [
            "tests/test_cases/test_login_pytest.py",
            f"--apk={apk_path}",
            "-v",
        ],
        plugins=[allure_pytest],
    )

    if result_login == 0:
        send_module_status("Login", "completed", "Login tests passed")
    else:
        send_module_status("Login", "failed", "Login tests failed")
        overall_ok = False

    if overall_ok:
        print("✅ All modules passed")
    else:
        print("⚠️ Some modules failed")

    print(f"\nTo view the detailed test report, run:\n  allure serve {allure_dir}")

    # Define paths
    # test_files = [
    #     "tests/test_cases/test_login_pytest.py",
    #     # "tests/test_cases/test_onboarding_pytest.py"
    # ]    
    # IMPORTANT: no --alluredir / --clean-alluredir here
    # result = pytest.main([
    #     *test_files,
    #     f"--apk={apk_path}",
    #     "-v",
    # ])
    
    # Run pytest with Allure options
    # result = pytest.main([
    #     *test_files,
    #     # f"--apk={apk_path}",
    #     f"--alluredir={allure_dir}",
    #     "--clean-alluredir",
    #     "-v"
    # ])

    # if result == 0:
    #     print("✅ Tests Passed")
    # else:
    #     print("⚠️ Tests Failed or encountered errors")
        
    # To view the report, run: allure serve allure-results
    # print(f"\nTo view the detailed test report, run: allure serve {allure_dir}")

if __name__ == "__main__":
    # run_tests_and_get_suggestions()
    # Example usage for manual testing
    # import sys
    # if len(sys.argv) > 1:
    #     apk = sys.argv[1]
    # else:
    #     print("Usage: python tests/test_runner.py <apk_path>")
    #     sys.exit(1)
    # run_tests_and_get_suggestions(apk)
    import sys

    if len(sys.argv) <= 1:
        print("Usage: python tests/test_runner.py <apk_path>")
        raise SystemExit(1)

    run_tests_and_get_suggestions(sys.argv[1])