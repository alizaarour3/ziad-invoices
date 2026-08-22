# Ziad Invoices Professional v3.3.22 - Login Full-Size UI Fix

This patch keeps the login page at its real desktop size instead of visually shrinking/zooming out.

## Target

- Full browser viewport (`100vw x 100vh`).
- Normal application visual scale (`zoom: 1`).
- Removes detected app-level shrinking transforms from login ancestors only.
- Desktop split approximately matches the supplied reference: 56.4% visual panel / 43.6% login panel.
- Login form remains large (up to 586px wide).
- Username/password fields and login button remain approximately 68px high on desktop.
- Mobile/tablet responsiveness remains enabled below 1000px.

## Apply

1. Extract the ZIP directly into the Ziad Invoices project root (same folder that contains `app/` and `start.py`).
2. Double-click `APPLY-LOGIN-100-PERCENT-SIZE-FIX.bat`.
3. Restart Ziad Invoices.
4. If Chrome/Edge itself was manually zoomed, press `Ctrl+0` once. Web code cannot change the browser's saved manual zoom level, but this patch removes application-level zoom-out/scaling.

## Safety

- Existing HTML entry files are backed up before modification.
- Invoice templates, database, Supabase settings, authentication logic and PDF logic are not modified.
- The fix activates only when the page contains the Arabic login labels: `تسجيل الدخول`, `اسم المستخدم`, and `كلمة المرور`.
