# Kontrol Noktaları Planı — Kritik Noktalar (sadeleştirilmiş)

> Karar: Her aşamaya kontrol koymak aşırı mühendislik (R9). Bunun yerine "hata olasılığı YÜKSEK × etki BÜYÜK" olan KRİTİK noktalara odaklan. Sonuç: 8 kapı değil, 3 kritik kontrol noktası.
> Tarih: 2026-06-24

---

## Kritik Nokta Seçimi (olasılık × etki)

| Aday adım | Olasılık | Etki | Kritik? |
|---|---|---|---|
| Soru kontrolü | Düşük | Düşük | ❌ Faz 3 |
| Şema linkleme | Orta | Orta | ❌ basit tut |
| SQL formatı temizleme | Düşük | Düşük | ❌ |
| **Güvenlik (SELECT-only)** | Düşük | **Felaket** | ✅ KRİTİK |
| **Grounding + EXPLAIN** | **Yüksek** | Yüksek | ✅ KRİTİK |
| Çalıştırma kurulumu | — | — | güvenli kurulum (kontrol değil) |
| **Anlam/sonuç denetimi** | **Yüksek** | **Yüksek** | ✅ KRİTİK |
| Rapor sayı güvenliği | — | Yüksek | mimari garanti (pandas) |

---

## 3 Kritik Kontrol Noktası

```
Soru → şema linkle → few-shot → SQL ÜRET
                                    │
   ╔════════════════════════════════▼═══════════════════════════╗
   ║ KONTROL 1 — GÜVENLİK (çalıştırmadan ÖNCE)                   ║ felaket önler
   ║   sadece-SELECT, injection, yazma/DDL engeli                ║
   ╚════════════════════════════════╤═══════════════════════════╝
                                     ▼
   ╔════════════════════════════════════════════════════════════╗
   ║ KONTROL 2 — DOĞRULUK (çalıştırmadan ÖNCE, DETERMİNİSTİK)    ║ en yüksek getiri
   ║   sözdizimi (sqlglot) + uydurma kolon (şema grounding)      ║ (bedava)
   ║   + EXPLAIN dry-run (çalıştırmadan şema/tip garantisi)       ║
   ╚════════════════════════════════╤═══════════════════════════╝
                                     ▼ geçti
                        ÇALIŞTIR (read-only + 8sn timeout)
                                     ▼
   ╔════════════════════════════════════════════════════════════╗
   ║ KONTROL 3 — ANLAM (çalıştırdıktan SONRA, KOŞULLU)           ║ "sessizce yanlış"ı yakalar
   ║   boş/NULL/anormal sinyal → varsa clause-bazlı LLM-critic    ║ (sadece risk sinyalinde)
   ║   → güven skoru / "emin değilim, netleştir"                  ║
   ╚════════════════════════════════╤═══════════════════════════╝
                                     ▼
                         RAPOR (sayıyı pandas hesaplar)
```

---

## Neden bu 3 nokta ve bu konumlar

- **KONTROL 1 — Güvenlik / çalıştırmadan önce:** Etki felaket (silme/sızma) → "düşük olasılık × felaket" = pazarlıksız kontrol. Konum: SQL üretildikten hemen sonra, çalıştırmadan önce.
- **KONTROL 2 — Doğruluk / çalıştırmadan önce:** Uydurma kolon ve şemaya oturmayan SQL en yaygın LLM hatası. Deterministik (LLM yok), bedava, veriye dokunmadan yakalar → en yüksek getirili nokta. EXPLAIN, çalıştırmadan şema/tip uyumunu %100 garanti eder.
- **KONTROL 3 — Anlam / çalıştırdıktan sonra, koşullu:** "Çalışır ama yanlış cevap" SADECE burada yakalanır. Pahalı (LLM) olduğu için yalnızca risk sinyalinde (boş/anormal sonuç) tetiklenir → yerel modelde maliyet minimumda.

---

## Koda Yansıması

| Kontrol | Dosya | Tür | Maliyet |
|---|---|---|---|
| 1 — Güvenlik | `sql_guvenlik.py` (mevcut) | deterministik | ~0 |
| 2 — Doğruluk | yeni `sql_kontrol.py` + `db_sorgu.py` (EXPLAIN) | deterministik | ~0 |
| 3 — Anlam | `sql_kontrol.py` (LLM-critic) | koşullu LLM | sadece risk varsa |

`runner.py` bu 3 noktayı sırayla çağırır. Her noktada karar: **GEÇ / DÜZELT (self-correction, max 2 tur) / DUR+SOR ("emin değilim")**.

Mimari garantiler (kontrol değil ama doğruluğu koruyan tasarım):
- Rapor sayıları **pandas** ile hesaplanır, LLM yorumlar → sayı uydurma imkânsız.
- Çalıştırma read-only kullanıcı + read-only transaction + timeout.

---

## Fazlama

- **Faz 1 (şimdi):** Kontrol 1 (var) + Kontrol 2 (yeni, deterministik). En yüksek getiri, bedava. Self-correction tetikleyicisini bu kontrollere bağla.
- **Faz 3:** Kontrol 3 (koşullu LLM-critic, clause-bazlı) + güven skoru (RSL-SQL iki-aday) + "emin değilim / netleştir".
- **Gelecek işi:** Eğitilmiş selector (CHASE-SQL) — anlatılır, yapılmaz.

---

## Doğrulama
- Kontrol 2 birim testi: uydurma kolonlu SQL + şemaya oturmayan SQL → reddedilmeli.
- Kontrol 3 testi: çalışan-ama-yanlış SQL → critic yakalamalı.
- Gold set A/B: kontroller AÇIK vs KAPALI execution accuracy farkı → vitrin kanıtı ("doğruluk %X→%Y").
