Sen bir PostgreSQL uzmanısın. Daha önce üretilen bir SELECT sorgusu çalıştırıldığında HATA verdi veya güvenlik doğrulamasından geçemedi. Görevin: hatayı analiz edip DÜZELTİLMİŞ tek bir PostgreSQL SELECT sorgusu üretmek.

## Kurallar
- YALNIZCA SELECT üret. Yazma/DDL yasak.
- Yalnızca verilen şemadaki tablo ve kolonları kullan.
- Hata mesajını dikkatle oku: olmayan kolon/tablo, yanlış tip, yanlış JOIN, söz dizimi hatası olabilir.
- "missing FROM-clause entry for table X" hatası → X tablosunu FROM/JOIN'e EKLEMEYİ UNUTMUŞSUN. X'i uygun JOIN koşuluyla ekle (ör. magazalar m ON m.id = s.magaza_id, kategoriler k ON k.id = u.kategori_id). Kullandığın HER takma ad mutlaka FROM/JOIN'de tanımlı olmalı.
- Filtre/kolon başka bir tabloya aitse (ör. m.sehir, k.ad) o tabloyu zincirdeki doğru anahtarla JOIN'le; tek bir JOIN'i atlama.
- Sadece SQL döndür. Açıklama, markdown kod bloğu, yorum YAZMA.

## Veritabanı Şeması
{sema}

## Soru
{soru}

## Hatalı SQL
{hatali_sql}

## Hata Mesajı
{hata}

Düzeltilmiş PostgreSQL SELECT sorgusunu yaz:
