"""SentinelGuard surum bilgisinin tek kaynagi.

Yeni surum cikarirken sadece bu degeri degistirin ve ayni isimde bir
git etiketi (ornek: v0.2.0-beta) gonderin. Release workflow'u etiketi bu
degerle karsilastirir; uyusmazsa derleme durur.
"""

__version__ = "0.1.0-beta"

# Guncellemelerin okunacagi GitHub deposu (sahip/isim).
GITHUB_REPOSITORY = "sublimisking/SentinelGuard"
