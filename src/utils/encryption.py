"""
Encryption utilities for securing credentials
"""
from cryptography.fernet import Fernet
from config.settings import settings
import base64
import os


class EncryptionManager:
    """Handle encryption/decryption of sensitive data"""
    
    def __init__(self):
        if not settings.encryption_key:
            # Generate a new key if not provided
            self.key = Fernet.generate_key()
            print(f"⚠️  WARNING: No encryption key found. Generated new key:")
            print(f"   Add this to your .env file: ENCRYPTION_KEY={self.key.decode()}")
        else:
            self.key = settings.encryption_key.encode()
        
        self.cipher = Fernet(self.key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string"""
        if not plaintext:
            return ""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt a string"""
        if not encrypted_text:
            return ""
        decrypted = self.cipher.decrypt(encrypted_text.encode())
        return decrypted.decode()
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key"""
        return Fernet.generate_key().decode()


# Global encryption instance
encryption = EncryptionManager()


if __name__ == "__main__":
    # Test and generate key
    print("Generated Encryption Key:")
    print(EncryptionManager.generate_key())
