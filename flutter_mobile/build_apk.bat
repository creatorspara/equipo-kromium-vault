@echo off
echo ========================================================
echo   Equipo Kromium - Android APK Build Pipeline (Dart)
echo   Target: release APK
echo ========================================================
flutter pub get
flutter build apk --release
echo.
echo [✔] Output APK located at: build\app\outputs\flutter-apk\app-release.apk
pause
