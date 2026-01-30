# K_R_F

To install Scoop, shims, and Allure on Windows, follow these steps:

1. Install Scoop
Open PowerShell as Administrator and run:
--------------------------------------------
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex
--------------------------------------------

2. Install Allure using Scoop
After installing Scoop, close and reopen PowerShell (as a normal user), then run:
--------------------
scoop install allure
--------------------
Scoop will automatically create the shims directory and add it to your PATH.
The allure command will now be available globally via the shim at:
C:\Users\<YourUsername>\scoop\shims\allure
3. Verify Installation
----------------
allure --version
----------------
Check that Allure is installed and available:

Summary:

Scoop manages the installation.
Shims are created automatically by Scoop for all installed apps.
Allure is installed and accessible via the allure command.
You do not need to manually download shims; Scoop handles it for you.