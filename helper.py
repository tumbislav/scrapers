# encoding: utf-8

"""
File: helper.py

Helper classes and methods for the scrapers package.
"""
__author__ = 'Marko Čibej'


import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class ScraperException(Exception):
    """
    An exception for our needs.
    """
    def __init__(self, raised_in, description):
        """
        :param raised_in: the method and class where the exception occurred
        :param description: the description of the error
        """
        self.raised_in, self.description = raised_in, description

    def __str__(self):
        return 'Error in {}: {}'.format(self.raised_in, self.description)


class SimpleCrypt:
    """
    Provide simple symmetric encryption and decryption for strings.
    """
    def __init__(self, master_password: str):
        """
        Create a key from the master password provided. The master password is not stored.
        :param master_password: what the name says
        """
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b'unsafe salt',
                         iterations = 100000, backend=default_backend())
        key_material = master_password.encode()
        self.fernet = Fernet(base64.urlsafe_b64encode(kdf.derive(key_material)))

    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt the plaintext and return a url safe base64 representation of the cyphertext.
        :param plaintext: the plaintext
        :return: the b64 encoded cyphertext
        """
        return self.fernet.encrypt(plaintext.encode())

    def decrypt(self, token: bytes) -> Optional[str]:
        """
        The reverse of encrypt(). It traps the decryption exception and returns None if the decryption fails.
        :param token: the base64 encrypted cyphertext
        :return: the decrypted plaintext
        """
        try:
            b = self.fernet.decrypt(token)
            return b.decode()
        except InvalidToken:
            return None
