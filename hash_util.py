import hashlib

def generate_hash(password: str) -> str:
    """
    Generate a SHA-256 hash for the given password.

    :param password: The input string to hash.
    :return: The resulting hash as a hexadecimal string.
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

if __name__ == '__main__':
    user_input = input("Enter a string to hash: ")
    print("Hash:", generate_hash(user_input))