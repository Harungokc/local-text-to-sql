// ============================================================
//  Şirket-Sorgu — Freelance Hizmet & Tanıtım Dokümanı
//  Typst kaynak. Derleme:  typst compile sirket_sorgu_tanitim.typ
// ============================================================

#let primary = rgb("#0f4c5c")
#let accent  = rgb("#2a9d8f")
#let warn    = rgb("#c1440e")
#let soft    = rgb("#eef3f4")
#let softln  = rgb("#cfe0e2")
#let ink     = rgb("#1c2526")

// İletişim sabitleri
#let AD     = "Harun Gökçe"
#let EPOSTA = "harungokce70@gmail.com"
#let TEL    = "0506 155 46 42"
#let REPO   = "github.com/Harungokc/local-text-to-sql"
#let REPO_URL = "https://github.com/Harungokc/local-text-to-sql"

#set document(title: "Şirket-Sorgu — Yerel Text-to-SQL (Freelance Hizmet)", author: AD)
#set text(font: ("Helvetica Neue", "Arial", "Libertinus Serif"), size: 10.5pt, lang: "tr", fill: ink)
#set par(justify: true, leading: 0.7em)
#set heading(numbering: none)

// --- Başlık stilleri ---
#show heading.where(level: 1): it => {
  pagebreak(weak: true)
  block(spacing: 1.2em)[
    #set text(size: 19pt, weight: "bold", fill: primary)
    #it.body
    #v(-6pt)
    #line(length: 100%, stroke: 2pt + accent)
  ]
}
#show heading.where(level: 2): it => block(above: 1.2em, below: 0.6em)[
  #set text(size: 13pt, weight: "bold", fill: primary)
  #it.body
]
#show heading.where(level: 3): it => block(above: 0.9em, below: 0.4em)[
  #set text(size: 11.5pt, weight: "bold", fill: accent)
  #it.body
]
#show link: it => underline(text(fill: accent, it))
#show raw.where(block: false): it => box(fill: soft, inset: (x: 3pt, y: 0pt), outset: (y: 3pt), radius: 2pt, text(font: "DejaVu Sans Mono", size: 9pt, it))
#show raw.where(block: true): it => block(fill: rgb("#0d1f24"), inset: 10pt, radius: 4pt, width: 100%, text(font: "DejaVu Sans Mono", size: 8.5pt, fill: rgb("#e8eef0"), it))

// --- Yardımcılar ---
#let kutu(baslik, govde, renk: accent) = block(
  width: 100%, fill: soft, inset: 10pt, radius: 4pt, stroke: (left: 3pt + renk), spacing: 1em,
)[
  #text(weight: "bold", fill: renk)[#baslik] \
  #govde
]
#let nod(govde, renk: primary, koyu: false) = align(center, box(
  width: 92%, fill: if koyu { renk } else { soft }, inset: 8pt, radius: 4pt, stroke: 1pt + renk,
  text(fill: if koyu { white } else { ink }, weight: if koyu { "bold" } else { "regular" }, size: 9.5pt, govde),
))
#let ok = align(center, text(fill: accent, size: 14pt, weight: "bold")[↓])

// İletişim bloğu (kapanış + CTA için)
#let iletisim_blok = block(
  width: 100%, fill: primary, inset: 14pt, radius: 6pt,
)[
  #set text(fill: white)
  #text(size: 14pt, weight: "bold")[İletişim — Şirketinizde Kuralım] \
  #v(4pt)
  #grid(columns: (auto, 1fr), gutter: 8pt, row-gutter: 4pt,
    text(fill: rgb("#a9d6cf"))[Ad:], [#AD — Freelance Yapay Zekâ & Yazılım Geliştirici],
    text(fill: rgb("#a9d6cf"))[E-posta:], [#EPOSTA],
    text(fill: rgb("#a9d6cf"))[Telefon:], [#TEL],
    text(fill: rgb("#a9d6cf"))[GitHub:], [#REPO],
  )
  #v(4pt)
  #text(size: 11pt, weight: "bold", fill: rgb("#7CFFB2"))[Bu sistemi şirketinizin verisiyle denemek veya kurmak için iletişime geçin.]
]

// ============================================================
//  KAPAK
// ============================================================
#set page(paper: "a4", margin: (x: 2.0cm, y: 2.0cm), numbering: none)

// Üst freelancer şeridi
#block(width: 100%, fill: primary, inset: 10pt, radius: 4pt)[
  #set text(fill: white, size: 10pt)
  #grid(columns: (1fr, auto), column-gutter: 16pt, align: (left + horizon, right + horizon),
    [#text(weight: "bold", size: 11pt)[#AD] — Freelance Yapay Zekâ & Yazılım Geliştirici],
    [#EPOSTA  ·  #TEL],
  )
]

#v(2.2cm)
#align(center)[
  #text(size: 12pt, fill: accent, weight: "bold", tracking: 2pt)[YEREL · GİZLİLİK-KORUMALI · YAPAY ZEKÂ]
  #v(0.7cm)
  #text(size: 30pt, weight: "bold", fill: primary)[Şirket-Sorgu]
  #v(0.1cm)
  #text(size: 17pt, fill: ink)[Türkçe Soru → SQL → Otomatik Rapor]
  #v(0.4cm)
  #line(length: 40%, stroke: 2pt + accent)
  #v(0.6cm)
  #block(width: 82%)[
    #set text(size: 12pt)
    #set par(justify: false)
    *Şirketinizin verisine Türkçe soru sorun — kurulumunu biz yapalım.*
    Veriyi *hiç dışarı çıkarmadan*, tamamen yerel çalışan bir yapay zekâ ajanı:
    çalışan Türkçe sorar, sistem güvenli SQL üretir, çalıştırır ve doğrulanmış bir Türkçe rapor döndürür.
  ]
  #v(1.4cm)
  #grid(columns: (auto, auto), gutter: 14pt,
    align(right)[#text(weight: "bold")[Hazırlayan:] \ #text(weight: "bold")[Tarih:] \ #text(weight: "bold")[Sürüm:]],
    align(left)[#AD \ 29 Haziran 2026 \ Çalışan MVP],
  )
  #v(1.0cm)
  #kutu("Bu sistemi şirketinizde kuruyoruz", renk: primary)[
    Kendi veritabanınıza entegre eder, ihtiyacınıza göre özelleştirir ve eğitiriz. \
    *GitHub (açık kaynak):* #link(REPO_URL)[#REPO] \
    *İletişim:* #EPOSTA  ·  #TEL
  ]
]

// ============================================================
//  Bundan sonraki tüm sayfalarda: numara + iletişim footer'ı
// ============================================================
#set page(
  numbering: "1",
  footer: context [
    #line(length: 100%, stroke: 0.5pt + softln)
    #v(-4pt)
    #grid(columns: (1fr, auto),
      text(size: 7.5pt, fill: rgb("#5a6b6d"))[#AD · #EPOSTA · #TEL · #REPO],
      text(size: 7.5pt, fill: rgb("#5a6b6d"))[#counter(page).display()],
    )
  ],
)

// ============================================================
//  İÇİNDEKİLER
// ============================================================
#heading(level: 1)[İçindekiler]
#outline(title: none, depth: 1, indent: 1em)

= 1. Bu Sistemi Şirketinizde Kuruyoruz

Şirketinizin verisi var ama çoğu çalışan SQL bilmediği için ona ulaşamıyor. Hazır bulut çözümleri ise veriyi dışarı (OpenAI vb.) gönderiyor — birçok kurum için kabul edilemez. *Şirket-Sorgu* bu iki sorunu birden çözer: çalışanlar *Türkçe* sorar, cevap *saniyeler içinde* gelir ve *veri makineden hiç çıkmaz.*

Ben, *#AD*, bu sistemi *sizin verinize ve ihtiyaçlarınıza göre* kuruyorum.

== Sunduğum hizmetler
#grid(columns: (1fr, 1fr), gutter: 12pt,
  kutu("Kurulum & entegrasyon", renk: accent)[
    Sistemi şirketinizin sunucusuna/bilgisayarına kurar, *kendi veritabanınıza* (PostgreSQL, MySQL vb.) bağlarım. Veri yerinde kalır.
  ],
  kutu("Özelleştirme & eğitim", renk: accent)[
    Şemanıza özel örnekler, terimler ve raporlar; ekibinize kullanım eğitimi.
  ],
  kutu("Bakım & geliştirme", renk: accent)[
    Doğruluğu artırma, yeni soru türleri, performans ve sürüm güncellemeleri.
  ],
  kutu("Özel AI çözümleri", renk: accent)[
    Yalnızca bu sistemi değil; şirketinize özel *yapay zekâ ajanları ve otomasyonlar* da geliştiriyorum.
  ],
)

== Hangi sektörler için?
Sistem veritabanı-agnostiktir; veri analizi yapan *her sektöre* uyarlanır. Özellikle *gizlilik-hassas* sektörlerde yerel çalışma kritik avantajdır:

#align(center, table(
  columns: (1fr, 1.3fr),
  inset: 7pt, align: (left, left),
  stroke: 0.5pt + softln,
  fill: (_, y) => if y == 0 { primary } else if calc.odd(y) { soft } else { white },
  table.header(
    text(fill: white, weight: "bold")[Sektör],
    text(fill: white, weight: "bold")[Örnek kullanım],
  ),
  [Perakende & E-ticaret], [Satış, ciro, stok, kampanya ve ürün performansı analizi],
  [Muhasebe & Mali Müşavirlik], [Müşteri/cari verileri — gizliliği kritik, yerel çalışma şart],
  [Sağlık & Klinik], [Hasta/randevu verisi — KVKK gereği veri dışarı çıkamaz],
  [Hukuk Büroları], [Dosya/müvekkil verisi üzerinde gizli sorgulama],
  [Finans & Sigorta], [Regülasyon altında poliçe/işlem analizi],
  [Lojistik & Kargo], [Sevkiyat, teslimat süreleri, bölgesel performans],
  [Üretim & Fabrika], [Üretim, bakım, fire ve verimlilik raporları],
  [Turizm & Otelcilik], [Rezervasyon, doluluk, gelir (RevPAR) analizi],
  [Eğitim Kurumları], [Öğrenci/başarı verisi üzerinde güvenli raporlama],
  [Kamu & Belediye], [Vatandaş verisi — yurt içinde, yerelde kalmalı],
))

#kutu("Şirketinizde kuralım", renk: primary)[
  Kendi verinizle denemek veya kurmak için: *#EPOSTA*  ·  *#TEL*  ·  #link(REPO_URL)[#REPO]
]

= 2. Yönetici Özeti

Bu sistem, bir şirketin kendi veritabanına *doğal Türkçe ile* soru sorabilmesini sağlayan, *tamamen yerel (local) çalışan* bir text-to-SQL yapay zekâ ajanıdır. Kullanıcı "en çok ciro yapan 5 ürün hangisi?" diye sorar; sistem soruyu güvenli bir SQL sorgusuna çevirir, salt-okunur çalıştırır, sonucu işler ve *doğrulanmış* bir Türkçe rapor döndürür.

#kutu("Tek cümlede değer önermesi", renk: primary)[
  Kurumsal text-to-SQL hâlâ çözülmemiş zor bir problem (Spider 2.0 benchmark'ında GPT-4o bile yalnızca \~%10). Bu sisteme *mühendislik disipliniyle* ve *veriyi hiç dışarı çıkarmadan* yaklaşıldı.
]

#grid(columns: (1fr, 1fr), gutter: 14pt,
  kutu("Kimin için?", renk: accent)[
    - *İşletmeler:* SQL bilmeyen ekiplere self-servis veri analizi.
    - *Yöneticiler:* anında Türkçe rapor, dışa bağımlılık yok.
    - *Gizlilik-hassas kurumlar:* veri makineden hiç çıkmaz (KVKK/GDPR dostu).
  ],
  kutu("Ölçülen sonuç (3B model, dizüstü)", renk: accent)[
    - Temel/orta sorular: *%87–95 doğruluk*
    - İleri analitik (pencere fn., percentile): *\~%20* (sunucuda 7B/32B ile yükselir)
    - Güvenlik testi: *15/15* · Türetilmiş metrik: *3/3*
    - Tüm bu sayılar gerçekten ölçüldü — uydurma yok.
  ],
)

Ayırt edici yan tek bir model değil, *mimaridir*: şema linkleme, RAG few-shot örnekleme, çok-katmanlı güvenlik/doğruluk kontrolü, türetilmiş-metrik denetimi ve "sayıyı kod hesaplar, LLM yalnızca yorumlar" ilkesiyle *halüsinasyonsuz* rapor.

= 3. Sorabileceğiniz Soru Türleri

Sistem şemanızı *çalışma anında* okur; aşağıdaki soru türlerini Türkçe sorabilirsiniz. (İşaretli sayılar bu demoda *gerçekten ölçülmüş* sonuçlardır.)

== Satış & ciro
- "en çok ciro yapan 5 ürün hangisi?"
- "şehir bazında toplam satış adedi nedir?"
- "Pınar markasının toplam cirosu ne kadar?"

== Oran & pay soruları (ölçülmüş gerçek sonuçlar)
- "İçecek kategorisinin toplam ciro içindeki payı nedir?" → *%13,1*
- "İstanbul, Antalya'dan kaç kat fazla ciro yaptı?" → *\~3,51 kat*
- "en çok ciro yapan ürünün toplam içindeki payı nedir?" → *%4,1*

#kutu("Neden oran soruları özel?", renk: primary)[
  Çoğu sistem yüzde/pay sorularında *yanlış paydadan* hesap yapar (örn. yalnızca ilk 5 ürünün toplamını alır). Bu sistem ayrı bir doğrulama katmanıyla (K3) *gerçek toplamı* çekip doğru yüzdeyi verir.
]

== Kampanya & indirim takibi
Verinizde kampanya/indirim alanları olduğunda şu sorular yanıtlanır:
- "X kampanyası döneminde ciro ne kadar arttı?"
- "indirimli ürünlerin toplam satışı nedir?"
- "kampanyalı vs kampanyasız ürünlerin cirosu nasıl karşılaştırılıyor?"
- "hangi kampanya en çok ek satış getirdi?"

#kutu("Dürüst not", renk: warn)[
  Demo veritabanında kampanya verisi *yoktur* — bu yüzden sistem demoda bu soruları (uydurmamak için) güvenle reddeder. Şirketinizin veritabanında kampanya/indirim tabloları olduğunda, sistem şemayı runtime okuduğu için bu sorular *otomatik* yanıtlanır hale gelir.
]

== Karşılaştırma & trend
- "bu ay ile geçen ayın cirosunu karşılaştır"
- "son 7 günde günlük ciro nasıl?"

== Stok / müşteri (verinize göre)
- "stok azalan ürünler hangileri?"  ·  "en çok alışveriş yapan müşteriler kim?"
(Bu alanlar veritabanınızda varsa yanıtlanır; yoksa sistem "bu veri yok" der, uydurmaz.)

= 4. Problem: Text-to-SQL Neden Zor, Gizlilik Neden Önemli?

== Zorluk gerçek
Basit akademik testlerde (Spider 1.0) en iyi sistemler \~%86–91 başarıya ulaşır. Ama *gerçek kurumsal şemalarda* (Spider 2.0 — 1000+ kolonlu veritabanları, 100+ satırlık SQL) tablo tersine döner:

#align(center, table(
  columns: (1fr, auto),
  inset: 8pt, align: (left, center),
  stroke: 0.5pt + softln,
  fill: (_, y) => if y == 0 { primary } else { white },
  table.header(
    text(fill: white, weight: "bold")[Benchmark / Sistem],
    text(fill: white, weight: "bold")[Doğruluk],
  ),
  [Spider 1.0 (basit, akademik)], [\~%86–91],
  [BIRD (gerçekçi, gürültülü)], [en iyi %81.95 / insan %92.96],
  [*Spider 2.0 — GPT-4o (gerçek kurumsal)*], [*\~%10*],
  [Spider 2.0 — o1-preview], [\~%21],
))

#kutu("Çıkarım", renk: warn)[
  Model seçimi tek başına belirleyici *değil*. Doğruluğu *mimari* belirler — retrieval, şema linkleme, kontrol katmanları, semantik denetim. Sistemin neden "tek model + tek atış" değil de katmanlı bir pipeline olarak tasarlandığının birinci-elden gerekçesi budur.
]

== Gizlilik: şirketlerin asıl korkusu
Çoğu hazır çözüm soruyu ve şemayı bir bulut API'sine gönderir — yani *veri şirketten çıkar.* Birçok kurum için bu pazarlıksız bir engeldir. Bu sistem baştan sona *yerel modelle* çalışır: soru, şema ve veri bilgisayardan/sunucudan *hiç dışarı çıkmaz*.

= 5. Bu Sistemi Ne Ayrıştırıyor?

#align(center, table(
  columns: (1fr, 1.2fr),
  inset: 8pt, align: (left, left),
  stroke: 0.5pt + softln,
  fill: (_, y) => if y == 0 { primary } else if calc.odd(y) { soft } else { white },
  table.header(
    text(fill: white, weight: "bold")[Sıradan demo],
    text(fill: white, weight: "bold")[Bu sistem],
  ),
  [Bulut API → veri dışarı çıkar], [*%100 yerel* — gizlilik-korumalı],
  [SQL'i körü körüne çalıştırır], [*Çok-katmanlı güvenlik* (read-only kullanıcı + read-only transaction + AST denetimi + timeout)],
  ["Çalışıyor" der, kanıt yok], [*Dürüst doğruluk ölçümü* (kendi gold set + execution accuracy)],
  [Tek model, tek atış], [*Araştırma-temelli mimari* (şema linkleme + few-shot + self-correction)],
  [Sayıyı LLM uydurur], [*Sayıyı pandas hesaplar*, LLM yalnızca yorumlar → halüsinasyon yok],
))

= 6. Mimari: Uçtan Uca Akış

Sistem bir soruyu, her adımı denetlenen bir hat üzerinden cevaba dönüştürür:

#v(4pt)
#nod("Türkçe Soru", renk: accent, koyu: true)
#ok
#nod("K0 · Eksik-kavram guard'ı (müşteri/kâr/stok şemada yoksa → \"bu veri yok\")")
#ok
#nod("Şema linkleme (ilgili tablolar) + RAG few-shot (benzer örnekler)")
#ok
#nod("SQL ÜRET — yerel model, sıcaklık 0 (determinizm)")
#ok
#nod("K1 · GÜVENLİK (yalnızca-SELECT)  +  K2 · DOĞRULUK (şema grounding + EXPLAIN)")
#ok
#nod("ÇALIŞTIR — read-only kullanıcı + read-only transaction + timeout")
#align(center, text(fill: warn, size: 8.5pt)[→ hata olursa self-correction: hatayı modele geri besle (maks 2 tur)])
#ok
#nod("K3 · ANALİZ DOĞRULAMA (türetilmiş metrik / pay güvenliği)")
#ok
#nod("RAPOR — pandas hesaplar, LLM yalnızca yorumlar")
#ok
#nod("SADAKAT KAPISI — anlatımdaki her sayı/isim olgularda var mı?")
#ok
#nod("Doğrulanmış Türkçe Rapor + Denetim İzi", renk: accent, koyu: true)

#v(6pt)
#kutu("Modüler tasarım")[
  Her katman tek sorumluluk taşır ve ayrı dosyadadır: `sql_guvenlik.py` (güvenlik), `sql_kontrol.py` (doğruluk), `analiz_kontrol.py` (metrik denetimi), `sema.py` (şema), `retrieval.py` (few-shot/RAG), `rapor.py` (rapor), `db_sorgu.py` (read-only DB), `runner.py` (orkestratör).
]

= 7. Kontrol Katmanları: Sistemin Kalbi

Tasarımın merkezinde bir ilke var: *her adıma kontrol koymak aşırı mühendisliktir.* Bunun yerine "hata olasılığı × etki" en yüksek *kritik noktalara* odaklanıldı. Ve sıralama bilinçli: *önce ucuz deterministik kontroller, en son pahalı LLM.*

#align(center, table(
  columns: (auto, 1.4fr, auto, auto),
  inset: 7pt, align: (center, left, center, center),
  stroke: 0.5pt + softln,
  fill: (_, y) => if y == 0 { primary } else if calc.odd(y) { soft } else { white },
  table.header(
    text(fill: white, weight: "bold")[Kontrol],
    text(fill: white, weight: "bold")[Ne yakalar],
    text(fill: white, weight: "bold")[Tür],
    text(fill: white, weight: "bold")[Maliyet],
  ),
  [*K0*], [Şemada karşılığı olmayan kavram (müşteri, kâr, stok) → uydurma yerine "bu veri yok"], [deterministik], [\~0],
  [*K1*], [Yazma/silme/DDL/injection — yalnızca SELECT'e izin], [deterministik], [\~0],
  [*K2*], [Uydurma tablo/kolon (AST grounding) + EXPLAIN ile tip/şema garantisi], [deterministik], [\~0],
  [*K3*], [Türetilmiş metrik hatası (kesik sonuçta yanlış "pay/yüzde")], [deterministik], [\~1 ek sorgu],
  [*Sadakat*], [Anlatımda olgularda olmayan sayı/isim → reddet, deterministik özete düş], [deterministik], [\~0],
))

#kutu("Tasarım felsefesi", renk: accent)[
  *Kendinden emin yanlış cevap vermektense "emin değilim / bu veri yok" demek daha sağlamdır.* Koşul sağlanmazsa sistem metriği bastırır ve çekince ekler. Dürüstlük, hem doğruluk hem güven kazandırır.
]

= 8. Halüsinasyonsuz Rapor

Rapor katmanı *hibrit* tasarlandı çünkü "LLM hesaplasın" güvenilmez (akademik testlerde sayısal doğruluk \~%78):

#grid(columns: (1fr, 1fr, 1fr), gutter: 10pt,
  nod("1. ozetle()\nDETERMİNİSTİK\npandas hesaplar", renk: primary),
  nod("2. icgoru_sec()\nKURAL TABANLI\nen önemli bulgular", renk: primary),
  nod("3. anlat()\nLLM YALNIZCA DİL\nTürkçe yorum", renk: accent, koyu: true),
)

#v(4pt)
Tüm sayılar (toplam, ortalama, pay, sıralama) *kod* tarafından hesaplanır; LLM yalnızca akıcı Türkçe cümleyi yazar ve "verilen sayı dışında rakam üretme" talimatı alır. Üstüne *sadakat kapısı*: anlatımdaki her sayı/isim yapılandırılmış olgularda yoksa, anlatım reddedilip %100 sadık deterministik özete düşülür.

#kutu("Gerçek çıktı — \"en çok ciro yapan 5 ürün hangisi?\"")[
  ```
  ÜRETİLEN SQL:
    SELECT u.ad AS urun, SUM(s.toplam_tutar) AS ciro
    FROM satislar s JOIN urunler u ON u.id = s.urun_id
    GROUP BY u.ad ORDER BY ciro DESC LIMIT 5

  SONUÇ:  Dana Kuşbaşı 2.687.760 · Beyaz Peynir 2.244.220 · Kıyma 2.140.880 ...
  ÖZET :  Dana Kuşbaşı 1kg, tüm ciro (66.181.361) içinde %4.1 pay tutuyor.
  İZ   :  K0 ✓  K1 ✓  K2 ✓  Çalıştırma ✓  K3: gerçek toplam ayrı çekildi  Sadakat ✓
  ```
  Not: "pay" hesabı için payda (66.181.361) ayrı, güvenli bir sorguyla çekildi — LIMIT'li sonucun toplamı *değil*. Bu, K3'ün asıl işidir.
]

= 9. Veritabanı: Neden PostgreSQL?

PostgreSQL, gizlilik-korumalı ve güvenli bir text-to-SQL hattı için ideal özelliklere sahip:

#align(center, table(
  columns: (auto, 1fr),
  inset: 8pt, align: (left, left),
  stroke: 0.5pt + softln,
  fill: (_, y) => if y == 0 { primary } else if calc.odd(y) { soft } else { white },
  table.header(
    text(fill: white, weight: "bold")[Özellik],
    text(fill: white, weight: "bold")[Katkısı],
  ),
  [Salt-okunur kullanıcı (GRANT)], [Yazma/silme'yi *fiziksel olarak* imkânsız kılar — en güçlü koruma katmanı],
  [Read-only transaction], [Çalıştırma sırasında ikinci savunma hattı],
  [`EXPLAIN` (yan etkisiz)], [Sorguyu çalıştırmadan şema/tip uyumunu %100 doğrular (K2)],
  [`information_schema`], [Şemayı runtime'da okuma → kod içine gömülü DDL yok; *kendi DB'nizi* bağlayabilirsiniz],
  [Olgunluk & yaygınlık], [Kurumlarda zaten standart; ek lisans/maliyet yok],
))

== Hangi diğer veritabanlarıyla yapılabilir?
Mimari veritabanı-agnostiktir; SQL diyalekti değişse de yaklaşım aynıdır:

#align(center, table(
  columns: (auto, 1fr),
  inset: 7pt, align: (left, left),
  stroke: 0.5pt + softln,
  fill: (_, y) => if y == 0 { accent } else if calc.odd(y) { soft } else { white },
  table.header(
    text(fill: white, weight: "bold")[Veritabanı],
    text(fill: white, weight: "bold")[Not],
  ),
  [MySQL / MariaDB], [Çok yaygın; read-only kullanıcı + EXPLAIN mevcut, diyalekt farkları küçük],
  [SQLite], [Tek-dosya, kurulumsuz; küçük/yerel kullanım için ideal],
  [DuckDB], [Analitik (OLAP) için çok hızlı; CSV/Parquet üzerinde doğrudan SQL],
  [SQL Server / Oracle], [Kurumsal; diyalekt/izin modeli farklı ama aynı kontrol felsefesi geçerli],
))

= 10. Model & Sunucu: Hangisi Ne Kadar Yeterli?

Aynı kod hem dizüstüde küçük modelle, hem sunucuda büyük modelle çalışır — *tek değişen iki ortam değişkeni* (`YEREL_MODEL`, `VLLM_BASE_URL`).

#align(center, table(
  columns: (auto, auto, auto, 1fr),
  inset: 7pt, align: (left, center, center, left),
  stroke: 0.5pt + softln,
  fill: (_, y) => if y == 0 { primary } else if calc.odd(y) { soft } else { white },
  table.header(
    text(fill: white, weight: "bold")[Model],
    text(fill: white, weight: "bold")[Boyut],
    text(fill: white, weight: "bold")[Nerede],
    text(fill: white, weight: "bold")[Rol],
  ),
  [Qwen2.5-Coder *3B*], [1.9 GB], [Dizüstü/PC], [Gündelik raporlama (temel/orta) — %87–95],
  [Qwen2.5-Coder *7B*], [4.7 GB], [Sunucu/GPU], [Daha yüksek doğruluk, daha çok kullanıcı],
  [Qwen2.5-Coder *32B*], [\~18–24 GB], [Sunucu/GPU], [İleri analitik (pencere fn., karmaşık analiz)],
))

== Sunucuda çalıştırma (7B / 32B)
İleri analitik veya çok kullanıcı gerektiğinde sistem bir sunucuda büyük modelle çalışır. Veri yine *tek-kiracı* ve *dışarı çıkmadan*:

#grid(columns: (1fr, 1fr), gutter: 12pt,
  kutu("Kiralık GPU", renk: accent)[
    RunPod gibi sağlayıcılarda izole (tek-kiracı) GPU — örn. A6000 \~\$0.49/saat. *İhtiyaç anında aç, işin bitince kapat* → maliyet düşük. 32B'yi rahat taşır.
  ],
  kutu("Yurt içi / dedicated sunucu", renk: accent)[
    KVKK hassasiyeti yüksekse tam dedicated/fiziksel sunucu (yurt içi). Veri ülke dışına hiç çıkmaz.
  ],
  kutu("Şirketin kendi sunucusu", renk: accent)[
    Donanımınız varsa sistemi *sizin* sunucunuza kurarım — hiçbir dış bağımlılık olmadan.
  ],
  kutu("Servis altyapısı", renk: accent)[
    vLLM ile OpenAI-uyumlu, çok-istekli (batching) servis. Web arayüzü + API hazır.
  ],
)

#kutu("Bu kurulumu biz yapıyoruz", renk: primary)[
  Donanım seçimi, model kurulumu, güvenli ağ ve sizin verinize entegrasyon — uçtan uca tarafımızdan yapılır. Siz yalnızca soruları sorarsınız.
]

#kutu("3B'nin dürüst sınırı", renk: warn)[
  3B; pencere fonksiyonu, grup-başına-top-N, percentile gibi *ileri analitiği* dizüstüde tek başına çözemez (kavramsal sınır). Bu sorular için sunucuda 7B/32B devreye girer. "Küçükle başla, gerektiğinde büyüt" stratejisi.
]

= 11. Yerel (Local) Çalışmanın Avantajları

#grid(columns: (1fr, 1fr), gutter: 12pt,
  kutu("Gizlilik & uyum", renk: accent)[
    Veri, şema ve sorular makineden *hiç çıkmaz.* KVKK/GDPR hassas kurumlar için pazarlıksız avantaj.
  ],
  kutu("Sıfır API maliyeti", renk: accent)[
    Token başına ücret yok. Sorgu sayısı arttıkça maliyet *artmaz.* Bulut API'de her sorgu para demektir.
  ],
  kutu("Bağımsızlık", renk: accent)[
    İnternet kesintisi, API kotası, fiyat değişikliği *etkilemez.* Sistem tamamen sizin kontrolünüzde.
  ],
  kutu("Öngörülebilirlik", renk: accent)[
    Sabit donanımda *tutarlı* gecikme; dış servis yavaşlaması yok.
  ],
)

= 12. Doğruluk Kanıtı ve Test

Sistem "çalışıyor" demekle yetinmez; *ölçer.* Dört bağımsız test ekseni:

#align(center, table(
  columns: (auto, 1.4fr, auto),
  inset: 7pt, align: (left, left, center),
  stroke: 0.5pt + softln,
  fill: (_, y) => if y == 0 { accent } else if calc.odd(y) { soft } else { white },
  table.header(
    text(fill: white, weight: "bold")[Test],
    text(fill: white, weight: "bold")[Ne ölçer],
    text(fill: white, weight: "bold")[Sonuç],
  ),
  [`test_guvenlik.py`], [Yazma/injection reddi (K1)], [15/15],
  [`test_kontrol.py`], [Uydurma kolon/tablo reddi (K2)], [10/10],
  [`gold_set.py`], [Uçtan uca execution accuracy], [7/8 (\~%87)],
  [`metrik_test.py`], [Türetilmiş metrik doğruluğu (K3)], [3/3],
))

#kutu("Kontrol katmanlarının kanıtı")[
  K3 olmasaydı sistem "Dana Kuşbaşı, toplam ciro içinde %25.0" derdi (yanlış — sadece 5 satırın toplamı). K3 sayesinde *doğru* cevap: "%4.1" (gerçek toplam 66.181.361 ayrı çekilerek). Bu fark, mühendisliğin doğruluğa katkısının somut kanıtıdır.
]

= 13. Nasıl Kurulur ve Çalıştırılır

== Gereksinimler
- Python 3.11+ · PostgreSQL · #link("https://ollama.com")[Ollama] (yerel model çalıştırıcı)

== Adım adım
```bash
# 1) Repoyu klonla
git clone https://github.com/Harungokc/local-text-to-sql.git && cd local-text-to-sql

# 2) Sanal ortam + bağımlılıklar
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 3) Yerel modeli indir (Ollama açık olmalı)
ollama pull qwen2.5-coder:3b

# 4) Demo veritabanını kur
createdb sirket_demo
export DATABASE_URL="postgresql://$USER@localhost:5432/sirket_demo"
.venv/bin/python demo_veri.py

# 5) Few-shot örneklerini yükle
export SORGU_DATABASE_URL="postgresql://$USER@localhost:5432/sirket_demo"
.venv/bin/python seed_sema.py

# 6) Web arayüzünü başlat → tarayıcıda http://127.0.0.1:9000
.venv/bin/python -m uvicorn api:app --port 9000
```

#kutu("Üretimde dikkat", renk: warn)[
  Uygulama *salt-okunur* bir DB kullanıcısı kullanmalı. Gerçek şirket verisiyle kurulum, doğru izinler ve güvenli ağ ayarlarını içerir — bu kurulumu sizin için biz yapıyoruz.
]

= 14. Yol Haritası

#grid(columns: (1fr, 1fr), gutter: 12pt,
  kutu("Tamamlanan", renk: accent)[
    - Uçtan uca pipeline + 5 kontrol katmanı
    - Web arayüzü + REST API + terminal
    - Dürüst doğruluk ölçümü (4 test ekseni)
    - Açık kaynak repo + dokümanlar
  ],
  kutu("Sıradaki (Faz 3–4)", renk: primary)[
    - Koşullu LLM-critic + güven skoru ("emin değilim")
    - Intent-based retrieval + kolon budama (büyük şema)
    - Semantik metrik katmanı (sabit iş tanımları)
    - Sunucuda 32B + grafik üretimi
  ],
)

= 15. İletişim & Hizmet

Bu sistem, kurumsal text-to-SQL'in zor bir problem olduğunu kabul ederek ona *mühendislikle* ve *veriyi hiç dışarı çıkarmadan* yaklaşır. Doğruluğu modelden değil; katmanlı kontrol, RAG few-shot ve halüsinasyonsuz rapor *mimarisinden* alır.

*Sonuç:* dizüstünde bile çalışan, gündelik iş sorularını %87–95 doğrulukla yanıtlayan, sınırlarını dürüstçe belgeleyen bir asistan — ve gerektiğinde sunucuda büyük modele ölçeklenen bir mimari.

#v(0.5cm)
#iletisim_blok

#v(0.4cm)
#align(center, text(size: 9pt, fill: rgb("#7a8a8c"))[
  Açık kaynak: #link(REPO_URL)[#REPO]  ·  Bu sistemi şirketinize biz kuralım.
])
