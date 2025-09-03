import os
import json
import hashlib
from datetime import datetime
from cryptography.fernet import Fernet

class SecureLogger:
    def __init__(self, key=None):
        """
        Инициализация безопасного логгера
        
        Args:
            key (str, optional): Ключ для шифрования. Если не указан, будет сгенерирован новый.
        """
        if key:
            self.key = key.encode()
        else:
            self.key = Fernet.generate_key()
        self.fernet = Fernet(self.key)
        self.setup_dirs()
        
    def setup_dirs(self):
        """Создание необходимых директорий для логов"""
        os.makedirs('logs/raw', exist_ok=True)
        os.makedirs('logs/encrypted', exist_ok=True)
        os.makedirs('logs/keys', exist_ok=True)
        
        # Сохраняем ключ для последующей расшифровки
        key_file = f"logs/keys/key_{datetime.now().strftime('%Y%m%d_%H%M%S')}.key"
        with open(key_file, 'wb') as f:
            f.write(self.key)
    
    def _anonymize(self, data: str) -> str:
        """Анонимизация данных с помощью хеширования"""
        if not data:
            return "anonymous"
        return hashlib.sha256(data.encode()).hexdigest()[:12]
    
    def log_event(self, event_type: str, user_data: dict, content: str = "", additional_data: dict = None):
        """
        Логирование события с шифрованием и анонимизацией
        
        Args:
            event_type (str): Тип события (например, "message", "command", "error")
            user_data (dict): Данные пользователя
            content (str, optional): Содержимое сообщения или события
            additional_data (dict, optional): Дополнительные данные для логирования
        """
        # Анонимизируем пользовательские данные
        user_id_anon = self._anonymize(str(user_data.get('id', '')))
        username_anon = self._anonymize(user_data.get('username', ''))
        first_name_anon = self._anonymize(user_data.get('first_name', ''))
        last_name_anon = self._anonymize(user_data.get('last_name', ''))
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": self._anonymize(f"{datetime.now().timestamp()}{user_data.get('id', '')}"),
            "event_type": event_type,
            "user": {
                "id_anon": user_id_anon,
                "username_anon": username_anon,
                "first_name_anon": first_name_anon,
                "last_name_anon": last_name_anon,
                "language_code": user_data.get('language_code', ''),
                "is_bot": user_data.get('is_bot', False)
            },
            "metadata": {
                "platform": "telegram",
                "client": user_data.get('client', 'unknown'),
                "source": user_data.get('source', 'unknown')
            },
            "content": self.fernet.encrypt(content.encode()).decode() if content else "",
            "additional_data": self.fernet.encrypt(
                json.dumps(additional_data or {}).encode()
            ).decode() if additional_data else ""
        }
        
        self._save_log(log_entry)
        return log_entry["event_id"]
    
    def _save_log(self, log_entry: dict):
        """Сохранение лога в файлы"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Нешифрованная версия (только для отладки, без конфиденциальных данных)
        safe_log_entry = log_entry.copy()
        safe_log_entry.pop("content", None)
        safe_log_entry.pop("additional_data", None)
        
        with open(f'logs/raw/{date_str}.ndjson', 'a', encoding='utf-8') as f:
            f.write(json.dumps(safe_log_entry, ensure_ascii=False) + '\n')
            
        # Полная шифрованная версия
        encrypted = self.fernet.encrypt(json.dumps(log_entry, ensure_ascii=False).encode())
        with open(f'logs/encrypted/{date_str}.enc', 'ab') as f:
            f.write(encrypted + b'\n---RECORD---\n')
    
    def read_logs(self, date_str: str, decrypt: bool = False):
        """
        Чтение логов за определенную дату
        
        Args:
            date_str (str): Дата в формате YYYY-MM-DD
            decrypt (bool): Расшифровать ли содержимое
            
        Returns:
            list: Список лог-записей
        """
        logs = []
        
        if decrypt:
            # Чтение и расшифровка зашифрованных логов
            encrypted_file = f'logs/encrypted/{date_str}.enc'
            if os.path.exists(encrypted_file):
                with open(encrypted_file, 'rb') as f:
                    content = f.read()
                
                records = content.split(b'\n---RECORD---\n')
                for record in records:
                    if record.strip():
                        try:
                            decrypted = self.fernet.decrypt(record)
                            logs.append(json.loads(decrypted.decode()))
                        except Exception as e:
                            print(f"Ошибка расшифровки: {e}")
        else:
            # Чтение нешифрованных логов
            raw_file = f'logs/raw/{date_str}.ndjson'
            if os.path.exists(raw_file):
                with open(raw_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            logs.append(json.loads(line))
        
        return logs
    
    def get_encryption_key(self):
        """Получение ключа шифрования для последующего использования"""
        return self.key.decode()
    
    def cleanup_old_logs(self, days: int = 30):
        """Очистка старых логов"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Удаляем старые raw логи
        for filename in os.listdir('logs/raw'):
            if filename.endswith('.ndjson'):
                file_date = datetime.strptime(filename.split('.')[0], '%Y-%m-%d')
                if file_date < cutoff_date:
                    os.remove(os.path.join('logs/raw', filename))
        
        # Удаляем старые encrypted логи
        for filename in os.listdir('logs/encrypted'):
            if filename.endswith('.enc'):
                file_date = datetime.strptime(filename.split('.')[0], '%Y-%m-%d')
                if file_date < cutoff_date:
                    os.remove(os.path.join('logs/encrypted', filename))
        
        # Удаляем старые ключи (с осторожностью!)
        for filename in os.listdir('logs/keys'):
            if filename.startswith('key_') and filename.endswith('.key'):
                try:
                    key_date_str = filename[4:-4]  # Извлекаем дату из имени файла
                    key_date = datetime.strptime(key_date_str, '%Y%m%d_%H%M%S')
                    if key_date < cutoff_date:
                        os.remove(os.path.join('logs/keys', filename))
                except ValueError:
                    # Если не удается распарсить дату из имени файла, пропускаем
                    pass

# Создаем глобальный экземпляр логгера для простоты использования
logger = SecureLogger()

if __name__ == "__main__":
    # Пример использования
    test_user = {
        'id': 123456789,
        'username': 'testuser',
        'first_name': 'Test',
        'last_name': 'User',
        'language_code': 'ru',
        'is_bot': False
    }
    
    event_id = logger.log_event(
        event_type="test",
        user_data=test_user,
        content="Тестовое сообщение",
        additional_data={"test_field": "test_value"}
    )
    
    print(f"Записано событие с ID: {event_id}")
    
    # Чтение логов за сегодня
    today = datetime.now().strftime("%Y-%m-%d")
    logs = logger.read_logs(today)
    print(f"Найдено {len(logs)} записей за сегодня")
    
    # Чтение с расшифровкой
    encrypted_logs = logger.read_logs(today, decrypt=True)
    print(f"Найдено {len(encrypted_logs)} зашифрованных записей за сегодня")
