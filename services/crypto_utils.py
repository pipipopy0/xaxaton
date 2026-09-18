
from cryptography.fernet import Fernet

class CryptographyService:
    def __init__(self, key = None):
        if key is None:
            self.key = Fernet.generate_key()
        else:
            self.key = key.encode() if isinstance(key, str) else key
        self.cipher_suite = Fernet(self.key)
    def encrypt(self, text):
        return self.cipher_suite.encrypt(text.encode()).decode()
    def decrypt(self, encrypted_text):
        return self.cipher_suite.decrypt(encrypted_text.encode()).decode()