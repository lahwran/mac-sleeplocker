#!/bin/bash

bashpolyglot="""'"

cd "$(dirname "$0")"
source ve/bin/activate
pypy "$0" "$@"
echo "doing su"
su antihabit -c "printf '\e]50;ClearScrollback\a';exec env bash"

cat > /dev/null << PYTHONCODE
endbashpolyglot="'"""


import timelock
from cryptography.fernet import Fernet
import base64
import hashlib
import sys
from datetime import timedelta
import random
import string
import json
import os
random = random.SystemRandom()

timelocked = json.load(open(os.path.join(os.path.dirname(__file__),
                        "timelocked.dat")))

if __name__ == "__main__":
    if "social" in sys.argv:
        data = raw_input("paste encrypted data: ").strip()
        print decrypt(raw_input("master password: "), data)
    elif "makesocial" in sys.argv:
        data = raw_input("paste admin password: ").strip()
    elif "newpassword" in sys.argv:
        delta = input("timedelta instance "
                      "(please type 'timedelta(your arguments)'): ")
        length = input("length of password: ")
        password = "".join(random.choice(string.lowercase + string.digits)
                            for x in range(length))
        masterpassword = raw_input("master password: ")
        print "password:", password
        print "generating timelock. will take exactly the delta you specified!"
        data = timelock.encrypt(masterpassword, delta, password)
        print "timelocked data:", json.dumps(data)
    else:
        print "starting timelock decrypt"
        masterpassword = raw_input("master password: ")

        iters, data = timelocked
        password = timelock.decrypt(masterpassword, iters, data)

        print password

    print "remember, follow admin password with master password for security"


bashpolyglot="""'"
PYTHONCODE
endbashpolyglot="'"""


