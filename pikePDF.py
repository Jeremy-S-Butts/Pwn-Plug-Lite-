import sys
import pikepdf
from tqdm import tqdm

# Validate command-line arguments
if len(sys.argv) < 3:
    print("Usage: python pikePDF.py <pdf_file> <wordlist_file>")
    sys.exit(1)

# the target PDF file
pdf_file = sys.argv[1]
# the word list file
wordlist = sys.argv[2]

# load password list
passwords = [line.strip() for line in open(wordlist, "r", encoding="utf-8", errors="ignore")]

# iterate over passwords
for password in tqdm(passwords, desc="Decrypting PDF"):
    try:
        # open PDF file
        with pikepdf.open(pdf_file, password=password) as pdf:
            # Password decrypted successfully, break out of the loop
            print("[+] Password found:", password)
            break
    except pikepdf._qpdf.PasswordError:
        # wrong password, just continue in the loop
        continue
