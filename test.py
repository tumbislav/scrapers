from helper import SimpleCrypt

master_password = input('Enter master password\n')
c = SimpleCrypt(master_password)
username = input('Enter username\n')
print(c.encrypt(username))
password = input('Enter password\n')
print(c.encrypt(password))
