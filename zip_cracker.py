from   tqdm   import   tqdm  
import   zipfile, sys
from tqdm import tqdm
import sys
import zipfile
 
# The zip file you want to crack its password
zip_file = sys.argv[1]
# The password list path you want to use
wordlist = sys.argv[2]
 
 # initialize the Zip File object
zip_file = zipfile.ZipFile(zip_file)
# count the number of words in this wordlist
n_words = len(list(open(wordlist, "rb")))
# print the total number of passwords
print("Total passwords to test:", n_words)

with zipfile.ZipFile(zip_file) as zf:
    with open(wordlist, "rb") as wordlist:
        for word in tqdm(wordlist, total=n_words, unit="word"):
            try:
                zf.extractall(pwd=word.strip())
            except:
                continue
            else:
                print("Password found:", word.decode().strip())
                exit(0)
print("[!] Password not found, try other wordlist.")
