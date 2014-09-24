#!/usr/bin/env python

import datetime
import time
import hashlib
import base64
from cryptography.fernet import Fernet

# note: I didn't bother to parallelize because I have a more than a half an
# hour of computation time before this will be needed

def generate_by_time(seed, delta):
    end = time.time() + delta.total_seconds()
    h = hashlib.sha256(seed).digest()
    iters = 0
    try:
        while time.time() < end:
            h = hashlib.sha256(h).digest()

            iters += 1
    except:
        print "exception after %r iters", iters
        print "time until end:", end - time.time()
        print "key is", base64.urlsafe_b64encode(h)
        raise

    return base64.urlsafe_b64encode(h), iters


def generate_by_iters(seed, iters):
    h = hashlib.sha256(seed).digest()
    for x in xrange(iters):
        h = hashlib.sha256(h).digest()
    return base64.urlsafe_b64encode(h)


def encrypt(keyseed, delta, message):
    key, iterations = generate_by_time(keyseed, delta)
    encrypted = Fernet(key).encrypt(message)
    return iterations, encrypted


def decrypt(keyseed, iterations, encrypted):
    key = generate_by_iters(keyseed, iterations)
    decrypted = Fernet(key).decrypt(encrypted)
    return decrypted


def test_timelock_1():
    keyseed = "12345"
    delta = datetime.timedelta(seconds=1)

    t1 = time.time()
    key, iters = generate_by_time(keyseed, delta)
    t2 = time.time()
    key2 = generate_by_iters(keyseed, iters)
    t3 = time.time()

    print "1:", t2 - t1
    print "2:", t3 - t2
    print "iters:", iters

    assert key == key2


def test_timelock_2():
    keyseed = "12345"
    delta = datetime.timedelta(seconds=1)

    t1 = time.time()
    iters, encrypted = encrypt(keyseed, delta, "message")
    t2 = time.time()
    decrypted = decrypt(keyseed, iters, encrypted)
    t3 = time.time()

    print "1:", t2 - t1
    print "2:", t3 - t2
    print "iters:", iters

    assert decrypted == "message"
