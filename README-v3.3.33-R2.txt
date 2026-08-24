Ziad Invoices v3.3.33-R2 - Locked File Installer Fix

This is the same consolidated v3.3.33 update, with a safer installer.

Fixes installer error:
PermissionError: [WinError 32] The process cannot access the file because it is being used by another process

How to use:
1. Close Ziad Invoices completely.
2. Close the CMD/PowerShell window that is running its server, if any.
3. Run APPLY-v3.3.33-R2-LOCKED-FILE-FIX.bat.
4. If Windows still reports a locked file, the installer prints the file and, when possible, the locking process. Close it and press ENTER to retry.
5. After SUCCESS, start Ziad Invoices and press Ctrl+F5 once.

The installer is transactional: if installation fails, it attempts to restore files changed during that run.
