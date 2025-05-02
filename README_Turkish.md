# Telegram Tepki İzleyici

Telegram Tepki İzleyici, bir Telegram sohbetindeki en çok tepki alan mesajları bulup listeleyen bir web uygulamasıdır.

## Özellikler

- Telegram gruplarında/kanallarında en çok tepki alan mesajları bulma
- Belirli zaman aralıklarında arama yapma (7 gün, 30 gün, 90 gün, 180 gün, tüm zamanlar)
- Arama geçmişini kaydetme ve görüntüleme
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
├── templates/             # HTML şablonları
├── app.py                 # Uygulama başlatıcı
├── .env                   # Çevre değişkenleri
└── requirements.txt       # Bağımlılıklar
```

## Kullanım

1. Ana sayfada bir Telegram sohbeti veya kanalı belirtin (kullanıcı adı veya ID ile)
2. Tarama yapmak istediğiniz zaman aralığını seçin
3. "Tepkileri Getir" butonuna tıklayın
4. Sonuçlar, tepki sayısına göre azalan sırada listelenecektir 