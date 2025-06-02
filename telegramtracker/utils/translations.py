"""
Translation module for the Telegram Reaction Tracker application.
This module contains translations of texts used throughout the application.
"""

# Desteklenen diller
LANGUAGES = {
    'tr': 'Türkçe',
    'en': 'English'
}

# Çeviri metinleri sözlüğü
translations = {
    # Genel
    'app_name': {
        'tr': 'Telegram Tepki İzleyici',
        'en': 'Telegram Reaction Tracker'
    },
    'new_search': {
        'tr': 'Yeni Arama',
        'en': 'New Search'
    },
    'history': {
        'tr': 'Geçmiş',
        'en': 'History'
    },
    'back': {
        'tr': 'Geri',
        'en': 'Back'
    },
    'search': {
        'tr': 'Ara',
        'en': 'Search'
    },
    
    # Index sayfası
    'index_description': {
        'tr': 'Bir Telegram sohbetindeki en çok tepki alan mesajları bulun.',
        'en': 'Find the most reacted-to messages in a Telegram chat.'
    },
    'chat_input_label': {
        'tr': 'Sohbet Kullanıcı Adı veya ID:',
        'en': 'Chat Username or ID:'
    },
    'chat_input_placeholder': {
        'tr': '@kullaniciadi veya -100123456789',
        'en': '@username or -100123456789'
    },
    'period_label': {
        'tr': 'Zaman Aralığı Seçin:',
        'en': 'Select Time Period:'
    },
    'period_7': {
        'tr': 'Son 7 Gün',
        'en': 'Last 7 Days'
    },
    'period_30': {
        'tr': 'Son 30 Gün',
        'en': 'Last 30 Days'
    },
    'period_90': {
        'tr': 'Son 3 Ay',
        'en': 'Last 3 Months'
    },
    'period_180': {
        'tr': 'Son 6 Ay',
        'en': 'Last 6 Months'
    },
    'period_all': {
        'tr': 'Tüm Zamanlar',
        'en': 'All Time'
    },
    'period_1': { # New key for 1 day
        'tr': 'Son 24 Saat',
        'en': 'Last 24 Hours'
    },
    'fetch_button': {
        'tr': 'Tepkileri Getir',
        'en': 'Fetch Reactions'
    },
    'loading_chats': {
        'tr': 'Sohbetler yükleniyor...',
        'en': 'Loading chats...'
    },
    'select_chat_placeholder': {
        'tr': 'Bir sohbet seçin',
        'en': 'Select a chat'
    },
    'chat_id_required_error': {
        'tr': 'Sohbet Kullanıcı Adı veya ID alanı zorunludur.',
        'en': 'Chat Username or ID field is required.'
    },

    # Fetch Settings
    'fetch_settings': {
        'tr': 'Fetch Ayarları',
        'en': 'Fetch Settings'
    },
    'filter_by_reactions': {
        'tr': 'En çok reaksiyon alan mesajları indir',
        'en': 'Download most reacted messages'
    },
    'download_limit_label': {
        'tr': 'İlk kaç mesaj indirilsin?',
        'en': 'Download first N messages?'
    },
    'download_limit_placeholder': {
        'tr': 'Örn: 100',
        'en': 'Ex: 100'
    },
    'download_limit_validation_error': {
        'tr': 'İndirme limiti için geçerli bir sayı girin (en az 1).',
        'en': 'Please enter a valid number for the download limit (at least 1).'
    },

    # Loading sayfası
    'loading_title': {
        'tr': 'Mesajlar Taranıyor',
        'en': 'Scanning Messages'
    },
    'loading_description': {
        'tr': 'Telegram API aracılığıyla mesajları tarıyoruz. Bu biraz zaman alabilir.',
        'en': 'We are scanning messages through the Telegram API. This might take a while.'
    },
    'messages_scanned': {
        'tr': 'Taranan Mesajlar:',
        'en': 'Messages Scanned:'
    },
    'please_wait': {
        'tr': 'Lütfen bekleyin...',
        'en': 'Please wait...'
    },
    
    # Results sayfası
    'results_title': {
        'tr': 'En Çok Tepki Alan Mesajlar',
        'en': 'Top Reacted Messages'
    },
    'error_title': {
        'tr': 'Bir Hata Oluştu',
        'en': 'An Error Occurred'
    },
    'try_again': {
        'tr': 'Tekrar Deneyin',
        'en': 'Try Again'
    },
    'reactions': {
        'tr': 'tepki',
        'en': 'reactions'
    },
    'view_message': {
        'tr': 'Mesajı Görüntüle',
        'en': 'View Message'
    },
    'page': {
        'tr': 'Sayfa',
        'en': 'Page'
    },
    'of': {
        'tr': '/',
        'en': 'of'
    },
    'previous': {
        'tr': 'Önceki',
        'en': 'Previous'
    },
    'next': {
        'tr': 'Sonraki',
        'en': 'Next'
    },
    'total_messages': {
        'tr': 'Toplam Mesaj:',
        'en': 'Total Messages:'
    },
    
    # History sayfası
    'history_title': {
        'tr': 'Arama Geçmişi',
        'en': 'Search History'
    },
    'timestamp': {
        'tr': 'Zaman',
        'en': 'Timestamp'
    },
    'chat': {
        'tr': 'Sohbet',
        'en': 'Chat'
    },
    'period': {
        'tr': 'Dönem (Gün)',
        'en': 'Period (Days)'
    },
    'messages_found': {
        'tr': 'Bulunan Mesajlar',
        'en': 'Messages Found'
    },
    'messages_scanned': {
        'tr': 'Taranan Mesajlar',
        'en': 'Messages Scanned'
    },
    'actions': {
        'tr': 'İşlemler',
        'en': 'Actions'
    },
    'view_results': {
        'tr': 'Sonuçları Görüntüle',
        'en': 'View Results'
    },
    'delete': {
        'tr': 'Sil',
        'en': 'Delete'
    },
    'no_history': {
        'tr': 'Arama geçmişi bulunamadı.',
        'en': 'No search history found.'
    },
    
    # History Results sayfası
    'history_results_title': {
        'tr': 'Geçmiş Arama Sonuçları',
        'en': 'Results for Past Search'
    },
    'search_chat': {
        'tr': 'Sohbet',
        'en': 'Chat'
    },
    'search_date': {
        'tr': 'Arama Tarihi',
        'en': 'Searched On'
    },
    'search_period': {
        'tr': 'Dönem',
        'en': 'Period'
    },
    'messages_found_count': {
        'tr': 'Bulunan Mesajlar',
        'en': 'Messages Found'
    },
    'no_results': {
        'tr': 'Bu geçmiş kaydı için sonuç bulunamadı.',
        'en': 'No results found for this history entry.'
    },
    'back_to_history': {
        'tr': 'Geçmişe Dön',
        'en': 'Back to History'
    },
    
    # Silme işlemi
    'confirm_delete': {
        'tr': 'Bu arama geçmişini silmek istediğinizden emin misiniz?',
        'en': 'Are you sure you want to delete this search history?'
    },
    'yes': {
        'tr': 'Evet',
        'en': 'Yes'
    },
    'no': {
        'tr': 'Hayır',
        'en': 'No'
    },
    'redirecting': {
        'tr': 'Yönlendiriliyor...',
        'en': 'Redirecting...'
    },
    'media_items_found': {
        'tr': 'medya öğesi bulundu',
        'en': 'media items found'
    },
    'downloading': {
        'tr': 'İndiriliyor...',
        'en': 'Downloading...'
    },
    'media_processed': {
        'tr': 'İşlenen Medya:',
        'en': 'Media processed:'
    },
    'downloading_description': {
        'tr': 'Tepki alan mesajlar için medya dosyalarını indiriyoruz. Bu işlem biraz zaman alabilir.',
        'en': 'We are downloading media files for messages with reactions. This might take a while.'
    },
    'delete_selected': {
        'tr': 'Seçili Olanı Sil',
        'en': 'Delete Selected'
    }
}

def get_text(key, lang='tr'):
    """Returns the translation for a specific key in the selected language."""
    if key not in translations:
        return key  # Return the key itself if key doesn't exist
    if lang not in translations[key]:
        return translations[key]['en']  # Return English if language doesn't exist
    return translations[key][lang]
