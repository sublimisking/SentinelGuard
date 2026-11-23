# SentinelGuard
A Windows laptop security application that detects suspicious activity, triggers alarms, and sends real-time mobile notifications.

## Güncellemeler

Uygulama açılışta ve **Ayarlar > Güncellemeler** üzerinden GitHub Releases'i
kontrol eder. Yeni sürüm varsa kurulum dosyasını indirir, SHA-256 özetini
doğrular ve sessiz kurulumu başlatır; kurulum bitince uygulama yeniden açılır.
Koruma aktifken veya başlatılırken güncelleme kurulmaz.

### Yeni sürüm yayınlama

1. `src/sentinelguard/version.py` içindeki `__version__` değerini artırın (ör. `0.2.0-beta`).
2. Commit edip etiketi gönderin:
   ```
   git tag v0.2.0-beta
   git push origin main v0.2.0-beta
   ```
3. `.github/workflows/release.yml` testleri çalıştırır, PyInstaller + Inno Setup ile
   `SentinelGuard-v0.2.0-beta-Setup.exe` ve `.sha256` dosyasını üretir ve GitHub
   Release yayınlar. `-beta` gibi ekli sürümler "pre-release" olarak işaretlenir.
