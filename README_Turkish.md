# Telegram Tepki İzleyici

> Tepki sayılarını takip ederek herhangi bir Telegram sohbetindeki veya kanalındaki en popüler ve ilgi çekici mesajları keşfetmenize yardımcı olan bir analiz aracı.

Telegram Tepki İzleyici, bir Telegram sohbetindeki en çok tepki alan mesajları bulup listeleyen bir web uygulamasıdır.
![image](https://github.com/user-attachments/assets/5af11792-5a1e-48fd-b1a0-a8fec436569a)

## Özellikler

- Telegram gruplarında/kanallarında en çok tepki alan mesajları bulma
- Belirli zaman aralıklarında arama yapma (7 gün, 30 gün, 90 gün, 180 gün, tüm zamanlar)
- Arama geçmişini kaydetme ve görüntüleme
- Geçmiş sayfasından toplu geçmiş kaydı silme.
- Tepki almış mesajlar için medya indirme (eğer "Tepkilere göre filtrele" seçeneği aktifse).
- Türkçe ve İngilizce dil desteği
- Tepki sayısına göre sıralanmış sonuçlar
- Mesaj bağlantıları (t.me)

## Kurulum

1. Gerekli paketleri yükleyin:
```
pip install -r requirements.txt
```

2. `.env` adında dosya oluşturun ve düzenleyin:
```
API_ID=Telegram_API_ID_Numaranız
API_HASH=Telegram_API_Hash_Değeriniz
PHONE_NUMBER=Ülke kodu ile birlikte
```

3. Telegram oturum dosyasını oluşturmak için:
```
python create_session.py
```
Bu işlem Telegram API ile kimlik doğrulaması yapacak ve uygulama için gerekli olan `session.session` dosyasını oluşturacaktır.

4. Uygulamayı çalıştırın:
```
python app.py
```

5. Tarayıcınızda `http://localhost:5001` adresine gidin.

## Teknik Detaylar

Bu uygulama aşağıdaki teknolojileri kullanır:

- Flask: Web uygulaması altyapısı
- Telethon: Telegram API'sı ile iletişim
- SQLite: Veritabanı
- HTML, CSS: Kullanıcı arayüzü

## Klasör Yapısı

```
telegramTracker/
│
├── telegramtracker/       # Ana paket
│   ├── core/              # Veritabanı işlemleri
│   ├── services/          # Telegram API iletişimi
│   ├── utils/             # Yardımcı işlevler (çeviriler, vb.)
│   └── web/               # Web rotaları
│
├── static/                # Statik dosyalar (CSS, JS, resimler, fontlar)
│   ├── css/
│   └── js/
├── templates/             # HTML şablonları
│   └── partials/          # Tekrar kullanılabilir şablon parçacıkları
├── app.py                 # Uygulama başlatıcı
├── .env                   # Çevre değişkenleri
└── requirements.txt       # Bağımlılıklar
```

## Kullanım

1. Ana sayfada bir Telegram sohbeti veya kanalı belirtin (kullanıcı adı veya ID ile)
2. Tarama yapmak istediğiniz zaman aralığını seçin
3. İsteğe bağlı olarak, yalnızca tepki almış mesajlar için medyaları işlemek ve indirmek üzere "Tepkilere göre filtrele" seçeneğini işaretleyin.
4. İsteğe bağlı olarak, medyaların indirileceği en iyi girişlerin (mesajlar veya gruplar) sayısı için bir "İndirme limiti" belirleyin.
5. "Tepkileri Getir" butonuna tıklayın
6. Sonuçlar, tepki sayısına göre azalan sırada listelenecektir

## Geçmiş Sayfası Kullanımı
![image](https://github.com/user-attachments/assets/cedc4840-7be2-4435-8ef3-a3b220c5b20b)

Geçmiş sayfası, önceki arama sorgularınızı ve sonuçlarını görüntülemenizi sağlar.
Tek tek geçmiş kayıtlarını silebilir veya birden çok kaydı aynı anda kaldırmak için onay kutularını ve "Seçilenleri Sil" düğmesini kullanabilirsiniz.
![image](https://github.com/user-attachments/assets/5e45eb68-ae18-424f-b13d-c4e0aaafbad0)
