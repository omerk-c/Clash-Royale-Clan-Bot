<div align="center">

# 🛡️ Clash Royale Clan Bot

**Discord üzerinden klan yönetimini otomatikleştiren, savaş takibi, aktivite skorlaması, rozet sistemi ve haftalık raporlama sunan kapsamlı bir yardımcı bot.**

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Discord.py](https://img.shields.io/badge/discord.py-2.3.0+-blue.svg)
![Database](https://img.shields.io/badge/database-SQLite-green.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

</div>

---

> ⚠️ **Tek klan / tek sunucu için tasarlanmıştır.** Bot, `.env` dosyasındaki tek bir `CLAN_TAG` üzerinden çalışır ve bildirim kanalları bot genelinde (sunucuya özel değil) tutulur. Birden fazla Discord sunucusuna eklenirse yalnızca dil tercihi sunucuya göre değişir; klan verisi ve kanal ataması ortaktır.

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Yetkilendirme Modeli](#-yetkilendirme-modeli)
- [Kurulum](#-kurulum)
- [Komut Listesi](#-komut-listesi)
- [Çoklu Dil (i18n)](#-çoklu-dil-i18n)
- [Proje Yapısı](#-proje-yapısı)
- [Otomatik Görevler](#-otomatik-görevler)
- [Veritabanı](#-veritabanı)
- [Bilinen Sınırlamalar](#-bilinen-sınırlamalar)
- [Katkıda Bulunma](#-katkıda-bulunma)

---

## ✨ Özellikler

### ⚔️ Savaş ve Klan Yönetimi
- Aktif River Race durumu, klan sıralaması, deste kullanımı
- Katkı sıralaması (madalya bazlı)
- Son 5 savaşın özeti
- Katılmayan (0 madalyalı) üyelerin listesi
- Üye tag/isim listesi

### 👥 Üye Takibi
- Katılım/ayrılış otomatik algılama (giden üyenin başka bir klana geçip geçmediğini API üzerinden kontrol eder)
  - 🟡 Başka klana geçti → yeni klan adıyla bildirilir
  - 🔴 Klansız → "atıldı" olarak işaretlenir
  - 🟢 Yeni katılım

### 📊 Aktivite ve Analiz
- **Aktivite Skoru (0-100):** Bağış (%30) + Savaş (%50) + Kupa (%20)
- Düşük skorlu üyeler için özelleştirilebilir liste
- İstatistiksel Elder/Co-Leader terfi önerileri
- `matplotlib` ile klan/rakip karşılaştırmalı grafik
- Normal dağılım tabanlı savaş sonucu tahmini

### 🏅 Rozet Sistemi
- 9 farklı rozet (First Blood, Fire Streak, Donation King, MVP, Legend, vb.)
- Her 6 saatte bir otomatik kontrol
- Rozet sayısına göre liderlik tablosu

### 🃏 Deste ve Diğer Araçlar
- Arena seviyesine göre deste önerisi, rastgele eğlence destesi
- Oyuncu bazlı deste/kart kullanım analizi
- Klan rekorları ve rekor kırılma geçmişi
- Haftalık otomatik/manuel performans raporu

---

## 🔐 Yetkilendirme Modeli

Bu bot **varsayılan olarak kilitlidir.** Sunucuya eklendiğinde hiçbir komut, aşağıdaki üç gruptan birine girmeyen kullanıcılar için çalışmaz:

1. Discord **Administrator** yetkisine sahip üyeler
2. `.env` içindeki `LEADER_ROLE_ID` rolüne sahip üyeler
3. `!grant_auth` komutuyla açıkça yetkilendirilmiş kullanıcılar

> Bu, sadece `grant_auth`/`revoke_auth` gibi yönetim komutlarıyla sınırlı değildir — `!clan`, `!wars` gibi bilgi amaçlı komutlar da dahil olmak üzere **tüm komutlar** bu kontrolden geçer. Botu ekledikten sonra hiçbir şeyin çalışmadığını görürseniz muhtemelen `LEADER_ROLE_ID` ayarlanmamıştır veya kullanıcı Administrator değildir.

| Komut | Açıklama | Kim kullanabilir |
| --- | --- | --- |
| `!grant_auth @kişi` (`!yetki_ver`) | Kullanıcıya bot kullanım yetkisi verir | Admin / Leader |
| `!revoke_auth @kişi` (`!yetki_al`) | Kullanıcının yetkisini geri alır | Admin / Leader |

---

## 🚀 Kurulum

### 1. Gereksinimler

- Python 3.10+
- Discord Bot Token — [Discord Developer Portal](https://discord.com/developers/applications)
- Clash Royale API Token — [Clash Royale Developer Portal](https://developer.clashroyale.com)
  *(CR API IP tabanlıdır — sunucunuzun IP adresini whitelist'e eklemeyi unutmayın.)*

### 2. Kurulum Adımları

```bash
# Depoyu klonlayın
git clone https://github.com/omerk-c/Clash-Royale-Clan-Bot
cd Clash-Royale-Clan-Bot

# Sanal ortam oluşturun ve etkinleştirin
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Bağımlılıkları kurun
pip3 install -r requirements.txt

# Ortam değişkenleri dosyasını oluşturun
cp .env.example .env
# .env dosyasını kendi token/anahtar değerlerinizle doldurun
```

### 3. Yapılandırma (`.env`)

```env
# Discord Bot Token
DISCORD_TOKEN=your_discord_bot_token

# Clash Royale API Anahtarı
CR_API_KEY=your_clash_royale_api_token

# Klan Tag'i (# işaretiyle birlikte)
CLAN_TAG=#YOURCLANTAG

# Varsayılan bildirim kanalı ID'si
CHANNEL_ID=discord_channel_id

# Leader rolü ID'si (yetkilendirme için)
LEADER_ROLE_ID=discord_leader_role_id
```

> ⚠️ `LEADER_ROLE_ID` girilmezse yalnızca Discord **Administrator** yetkisine sahip kullanıcılar botu kullanabilir.

### 4. Başlatma

```bash
python3 main.py
# veya
.venv/bin/python3 main.py
```

---

## 📖 Komut Listesi

Tüm komutlar `!` öneki ile kullanılır; parantez içindekiler Türkçe alias'lardır.

<details>
<summary><strong>⚔️ Savaş ve Klan</strong></summary>

| Komut | Alias | Açıklama |
| --- | --- | --- |
| `!clan` | `!klan` | Genel klan bilgisi |
| `!wars` | `!savaslar` | Aktif River Race durumu |
| `!contribution` | `!katki` | Katkı sıralaması (top 10) |
| `!warlog` | — | Son 5 savaşın özeti |
| `!list` | `!liste` | Üye listesi + roller |
| `!tags` | — | Üye isim ve Clash Royale tag'leri |
| `!inactive` | `!katilmayanlar`, `!sifircilar` | 0 madalyalı üyeler |

</details>

<details>
<summary><strong>📊 İstatistik ve Profil</strong></summary>

| Komut | Alias | Açıklama |
| --- | --- | --- |
| `!profile [#TAG / @kullanıcı]` | `!profil` | Detaylı oyuncu profili |
| `!activity` | `!aktivite` | Tüm üyelerin aktivite skoru (0-100) |
| `!kicklist [sayı]` | — | En düşük skorlu N kişi (varsayılan 5) |
| `!promotion` | `!terfi` | Elder/Co-Leader terfi önerisi |
| `!promotion_history #TAG` | `!terfi_gecmis` | Oyuncunun aktivite skoru geçmişi |
| `!graph` | `!grafik` | Klan/rakip fame karşılaştırma grafiği |
| `!player_board [#TAG]` | `!oyuncu_tablo` | Haftalık savaş performans tablosu |
| `!prediction [ekstra]` | `!tahmin` | Normal dağılımla savaş sonucu tahmini |
| `!battle_history [#TAG]` | `!savas_gecmisi` | Son 25 maçın detaylı analizi |
| `!deck_analysis #TAG` | `!deste_analiz` | Oyuncu deste/kart kullanım analizi |

</details>

<details>
<summary><strong>🏅 Rozetler ve Desteler</strong></summary>

| Komut | Alias | Açıklama |
| --- | --- | --- |
| `!badges [#TAG]` | `!rozetlerim` | Kazanılan rozetler |
| `!badge_leaderboard` | `!rozet_siralamasi` | Rozet liderlik tablosu |
| `!all_badges` | `!rozetler` | Tüm rozet açıklamaları |
| `!deck` | `!deste` | Rastgele meta deste önerisi |
| `!suggest_deck [arena]` | `!deste_oner` | Arena seviyesine göre meta deste |
| `!random_deck` | `!deste_rastgele` | Tamamen rastgele eğlence destesi |
| `!meta` | — | Tüm meta desteleri listeler |

</details>

<details>
<summary><strong>💰 Bağış</strong></summary>

| Komut | Alias | Açıklama |
| --- | --- | --- |
| `!donations` | `!bagis` | Klan bağış liderlik tablosu |
| `!leechers` | `!somuruculer` | Ortalamanın altında bağış yapıp fazla alanlar |

</details>

<details>
<summary><strong>📢 Kanal Yönetimi</strong> <sub>(Admin gerektirir)</sub></summary>

| Komut | Alias | Açıklama |
| --- | --- | --- |
| `!set_channel <tip> #kanal` | `!kanal_ayar` | Bildirim kanalı atar |
| `!remove_channel <tip>` | `!kanal_kaldir` | Kanal atamasını kaldırır |
| `!list_channels` | `!kanal_liste` | Tüm kanal atamalarını gösterir |
| `!test_channel <tip / all>` | `!kanal_test` | Test mesajı gönderir |

</details>

<details>
<summary><strong>🏆 Kayıtlar ve Sistem</strong></summary>

| Komut | Alias | Açıklama |
| --- | --- | --- |
| `!records` | `!rekorlar` | Tüm klan rekorları |
| `!record_history [kategori]` | `!rekor_gecmis` | Kırılan rekorların geçmişi |
| `!reset_record [kategori]` <sub>(Admin)</sub> | `!rekor_sifirla` | Rekorları sıfırlar |
| `!weekly` | `!haftalik` | Anlık haftalık rapor |
| `!weekly_setting` | `!haftalik_ayar` | Otomatik raporu aç/kapat |
| `!language <en/tr>` | `!dil` | Sunucu dilini değiştirir |
| `!grant_auth @kişi` <sub>(Admin/Leader)</sub> | `!yetki_ver` | Bot kullanım yetkisi verir |
| `!revoke_auth @kişi` <sub>(Admin/Leader)</sub> | `!yetki_al` | Bot kullanım yetkisini alır |
| `!help` | `!yardim` | Tüm komutları listeler |

</details>

<details>
<summary><strong>🌐 RoyaleAPI Ek Veri</strong> <sub>(deneysel, web scraping tabanlı)</sub></summary>

| Komut | Açıklama |
| --- | --- |
| `!royaleapi [#TAG]` | RoyaleAPI sayfasından ek klan istatistiği çeker |

> Bu komut, resmi Clash Royale API'sinin dışında, RoyaleAPI ve benzeri üçüncü parti sitelerin HTML/iç yapısını okuyarak çalışır. Sitelerin yapısı değiştiğinde önceden haber vermeksizin bozulabilir; bu durumda komut sessizce "veri alınamadı" mesajı döner, bot çökmez.

</details>

---

## 🌍 Çoklu Dil (i18n)

- **Varsayılan dil:** İngilizce (`en`)
- **Mevcut diller:** İngilizce (`en`), Türkçe (`tr`)
- Her Discord sunucusu kendi dil tercihini `!language` / `!dil` komutuyla ayarlayabilir; bu tercih veritabanında sunucuya özel olarak saklanır.
- Yeni bir dil eklemek için `locales/` klasörüne `en.json` yapısını birebir taklit eden yeni bir `[dil].json` dosyası ekleyin. `check.py` betiği iki dosya arasındaki anahtar tutarlılığını (parity) doğrular.

```bash
python3 check.py
```

---

## 🗂️ Proje Yapısı

```text
clashbot/
├── cogs/                        # Modüler bot komutları
│   ├── achievements.py          # Rozet sistemi
│   ├── activity.py              # Aktivite skoru ve kick listesi
│   ├── auth.py                  # Yetkilendirme (global check burada tanımlı)
│   ├── battle_history.py        # Maç geçmişi analizi
│   ├── channel_manager.py       # Bildirim kanalı yönetimi
│   ├── deck_suggest.py          # Meta deste önerici
│   ├── donations.py             # Bağış takibi
│   ├── prediction.py            # Savaş sonucu tahmini
│   ├── profile.py               # Oyuncu profil analizi
│   ├── promotion.py             # Terfi önerileri
│   ├── records.py               # Klan rekorları
│   ├── scraper.py               # RoyaleAPI / RCM web scraping (deneysel)
│   ├── settings.py              # Sunucu ayarları & dil
│   ├── stats.py                 # matplotlib grafik ve tablo
│   ├── tracker.py               # Değişiklik takibi & üye giriş/çıkış
│   ├── war.py                   # Savaş komutları, üye tag'leri, hatırlatıcı
│   └── weekly_report.py         # Haftalık rapor
├── data/                        # İlk çalıştırmada otomatik oluşur (.gitignore'da)
│   ├── clashbot.db              # Ana SQLite veritabanı
│   ├── authorized_users.json    # Yetkili kullanıcı listesi
│   ├── channel_config.json      # Kanal yapılandırması (bot geneli, sunucuya özel değil)
│   ├── clan_records.json        # Klan rekorları
│   └── linked_accounts.json     # Discord ↔ CR hesap eşlemesi
├── utils/                       # Yardımcı modüller
│   ├── channels.py              # Kanal yönetim modülü
│   ├── config.py                # .env okuma ve ayarlar
│   ├── cr_api.py                # Clash Royale API istemcisi
│   ├── database.py              # SQLite wrapper
│   └── i18n.py                  # Çoklu dil motoru
├── locales/                     # Dil dosyaları
│   ├── en.json
│   └── tr.json
├── main.py                      # Bot giriş noktası
├── check.py                     # Locale anahtar tutarlılık kontrolü
├── requirements.txt
├── .env.example
└── .env                         # Git'e dahil değil
```

---

## ⏱️ Otomatik Görevler

| Görev | Sıklık | Açıklama |
| --- | --- | --- |
| Değişiklik takibi | 10 dk | Bağış/savaş değişikliklerini algılar |
| Üye giriş/çıkış | 2 dk | Katılan/ayrılan/atılan üyeleri bildirir |
| Savaş hatırlatıcı | 30 dk | Savaş bitişine yakın deste uyarısı |
| Toplu rapor | 60 dk | Biriken değişiklikleri tek embed'de gönderir |
| Periyodik klan raporu | 2 saat | Klan durum özeti |
| Aktivite skoru | 6 saat | Tüm üyelerin skorunu veritabanına kaydeder |
| Rozet kontrolü | 6 saat | Yeni kazanılan rozetleri kontrol eder |
| Haftalık rapor | Pzt 08:00 (UTC) | Otomatik performans raporu |

---

## 🗄️ Veritabanı

Bot, verinin bütünlüğünü korumak ve I/O işlemlerini asenkron yürütmek için `aiosqlite` kullanır. Veritabanı (`data/clashbot.db`) ilk çalıştırmada otomatik oluşturulur.

| Tablo | İçerik |
| --- | --- |
| `players` | Oyuncu anlık verisi (kupa, seviye, bağış, vb.) |
| `donation_history` / `war_history` | Haftalık performans kayıtları |
| `activity_log` | Günlük aktivite skoru (zaman serisi analizi için) |
| `trophy_snapshots` | Günlük kupa anlık görüntüsü |
| `achievements` | Kazanılan rozetler *(`achievements.py` cog'u tarafından ilk çağrıda oluşturulur, merkezi şemanın parçası değildir)* |
| `server_settings` | Sunucuya özel ayarlar (tercih edilen dil vb.) |

---

## 🛡️ Güvenlik

- **SQL Injection koruması:** Veritabanı sorgularında izin verilen kolon adları whitelist ile kontrol edilir.
- **Rol tabanlı yetkilendirme:** Leader izni, metin bazlı rol isimleri yerine Discord Rol ID'si üzerinden doğrulanır (spoofing koruması).
- **Eşzamanlılık güvenliği:** JSON dosya işlemleri `asyncio.Lock` / `threading.Lock` ile korunur.
- **API token güvenliği:** Hassas bilgiler `.env` dosyasında tutulur ve `.gitignore` ile sürüm kontrolünün dışında bırakılır.

---

## ⚠️ Bilinen Sınırlamalar

Bu bölüm, projeyi kendi sunucunuzda çalıştırmadan önce bilmenizde fayda olan noktaları özetler:

- **Tek klan / bot geneli kanal yapılandırması:** `channel_config.json` sunucuya göre değil, bot sürecine göre tutulur. Bot birden fazla sunucuya eklenirse kanal atamaları sunucular arasında paylaşılır (üzerine yazılır).
- **`scraper.py` deneyseldir:** RoyaleAPI ve RoyaleClanManager gibi üçüncü parti sitelerin HTML/iç yapısına bağımlıdır; bu siteler değiştiğinde önceden haber vermeksizin bozulabilir. Hata durumunda bot çökmez, ilgili komut sadece veri döndürmez.
- **Test altyapısı yoktur:** Repo içinde birim test / CI pipeline bulunmuyor; `check.py` yalnızca locale dosyaları arasındaki anahtar tutarlılığını kontrol eder.
- **Varsayılan olarak kilitli:** Yukarıda [Yetkilendirme Modeli](#-yetkilendirme-modeli) bölümünde açıklandığı gibi, `LEADER_ROLE_ID` doğru ayarlanmadan hiçbir komut (yönetim komutları dahil, bilgi komutları dahil) çalışmaz.

---

## 🤝 Katkıda Bulunma

1. Depoyu fork'layın.
2. Yeni bir özellik dalı oluşturun: `git checkout -b feature/yeni-ozellik`
3. Değişikliklerinizi commit'leyin: `git commit -m 'feat: yeni özellik eklendi'`
4. Dalınızı push'layın: `git push origin feature/yeni-ozellik`
5. Bir Pull Request açın.

---

<div align="center">

📄 Lisans: [MIT](LICENSE)

</div>
