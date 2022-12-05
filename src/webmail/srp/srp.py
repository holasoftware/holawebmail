"""@package py3srp
  Secure Remote Password (SRP-6a) protocol implementation in pure Python3.

  Partly based on Tom Cocagne's CSRP, https://github.com/cocagne/csrp.

  References:
  * http://srp.stanford.edu
  * http://tools.ietf.org/html/rfc5054
  * http://tools.ietf.org/html/rfc2945
  * http://en.wikipedia.org/wiki/Secure_Remote_Password_protocol

  Copyright (c) 2015, Pablo Bleyer <pablo.N@SPAMbleyer.org>
  All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software without
   specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os
from .srp_defaults import *

def _randombytes(l):
    """Generate cryptosecure random bytes.
    @param l Number of bytes.
    @return bytearray with random data.
    """
    return os.urandom(l)

def _to_bytes(obj, ctx = None):
    """Convert object to byte array, with optional context.
    @param obj Object to convert.
    @param ctx Optional conversion context: byteorder if object is integer, encoding if object is string.
    @param Object bytearray.
    """
    if type(obj) == bytes:
        return obj # Idem
    elif type(obj) == int:
        return obj.to_bytes((obj.bit_length() + 7)//8, byteorder = ctx or DEFAULT_BYTEORDER)
    elif type(obj) == str:
        return bytes(obj, ctx or DEFAULT_ENCODING)
    else:
        return None # No conversion known

def _to_int(obj, ctx = None):
    """Convert object to integer, with optional context.
    @param obj Object to convert.
    @param ctx Optional conversion context: byteorder if object is integer, encoding if object is string.
    @return Respective integer number.
    """
    if type(obj) == int:
        return obj # Idem
    elif type(obj) == bytes:
        return int.from_bytes(obj, byteorder = ctx or DEFAULT_BYTEORDER)
    elif type(obj) == str:
        return int(obj, ctx or DEFAULT_RADIX)
    else:
        return None # No conversion known

def _pad(obj, bl, ctx = None):
    """Pad byte-string representation of number with zeroes to the left.
    @param obj Object to convert to padded bytes.
    @param bl Byte length of result.
    @param ctx Optional conversion context: byteorder if object is integer, encoding if object is string.
    @return Padded bytearray of object representation.
    """
    r = _to_bytes(obj, ctx)
    return b'\x00'*((bl+7)//8 - len(r))+r

def _H(hsh, *args, ctx = None):
    """Hash of concatenated argument objects.
    @param hsh Hash object to update.
    @param args Variable argument list of object to use for hash.
    @param ctx Optional conversion context: byteorder if objects are integers, encoding if objects are strings.
    @return Calculated hash digest.
    """
    for i in args:
        hsh.update(i if type(i) == bytes else _to_bytes(i, ctx))
    return hsh.digest()

def _calculate_x(hsf, slt, usn, pas, sep = DEFAULT_SEPARATOR, ctx = DEFAULT_BYTEORDER):
    """Calculate the user secret parameter.
    @param hsf Hash factory.
    @param slt Random salt bytes.
    @param usn Username string.
    @param pas Password string.
    @param sep Username-password separator.
    @param ctx Optional number byteorder.
    @return Integer value.
    """
    h_up = _H(hsf(), usn, sep, pas)
    return int.from_bytes(_H(hsf(), slt, h_up), byteorder = ctx)

def _calculate_M(hsf, g, N, I, s, A, B, K):
    """Calculate evidence message M hash.
    @param hsf Hash factory.
    @param g Group generator.
    @param N Group safe prime.
    @param I Username string.
    @param s Salt bytes.
    @param A User public value.
    @param B Verifier public value.
    @param K Private shared session key.
    @return Message value.
    """
    H_g = _H(hsf(), g)
    H_N = _H(hsf(), N)
    H_I = _H(hsf(), I)
    H_xor = bytes(map(lambda i: i[0]^i[1], zip(H_g, H_N)))

    s = _to_bytes(int(s, 16))

    return _H(hsf(), H_xor, H_I, s, A, B, K)

def salted_verification_key(usn, pas, hsf = DEFAULT_HASHER, gn = DEFAULT_GROUP, sls = DEFAULT_SALTSIZE, sep = DEFAULT_SEPARATOR):
    """Create salt and verification key from username and password.
    @param usn Username string.
    @param pas Password string.
    @param hsf Hash factory.
    @param gn Generator and safe prime group tuple.
    @param sls Byte size of salt.
    @param sep Username-password separator.
    @return Tuple of salt and verification key.
    """
    s = _randombytes(sls) # Cryptosecure random bytes
    x = _calculate_x(hsf, s, usn, pas, sep)
    v = pow(gn[0], x, gn[1])
    return s, v


class User:
    "SRP user (client) class."
    def __init__(self, hsf = DEFAULT_HASHER, gn = DEFAULT_GROUP, sep = DEFAULT_SEPARATOR):
        """Initialize user object.
        @param hsf Hash factory.
        @param gn Generator and safe prime group tuple.
        @param sep Username-password separator.
        """
        self.hasher = hsf
        self.username = ''
        self.password = ''
        self.separator = sep
        self.g = gn[0]
        self.N = gn[1]

        l = self.N.bit_length()
        self.k = _to_int(_H(self.hasher(), self.N, _pad(self.g, l)))

        self.a = 0
        self.A = 0
        self.S = 0
        self.M = b''
        self.H_AMK = b''
        self.session_key = b''
        self.auth = False

    def start_authentication(self, usn, pas, scs = DEFAULT_SECRETSIZE):
        """Start authentication procedure.
        @param usn Username string.
        @param pas Password string.
        @param scs Byte size of secret private value.
        @return User public value.
        """
        self.username = usn
        self.password = pas
        self.a = self.get_random_ephemeral(scs)
        self.A = pow(self.g, self.a, self.N)
        return self.A

    def is_invalid_ephemeral(self, a):
        return pow(self.g, a, self.N) == 0

    def get_random_ephemeral(self, scs):
        a = _to_int(_randombytes(scs))

        while self.is_invalid_ephemeral(a):
            a = _to_int(_randombytes(scs))

        return a

    def process_challenge(self, slt, ver_B):
        """Process verifier challenge calculating session key, premaster secret and evidence message.
        @param slt Salt value.
        @param ver_B Verifier public value.
        @return Evidence message on success, None on error.
        """
        ver_B = _to_int(ver_B)

        l = self.N.bit_length()
        u = _to_int(_H(self.hasher(), _pad(self.A, l),  _pad(ver_B, l)))
        x = _calculate_x(self.hasher, slt, self.username, self.password, self.separator)


        # Safety check
        if ver_B == 0 or u == 0:
            return None

        # Premaster secret, S = (B - k*(g^x)) ^ (a + u*x)
        t1 = ver_B - self.k * pow(self.g, x, self.N)
        t2 = self.a + u * x
        self.S = pow(t1, t2, self.N)
        # Shared session key
        self.session_key = _H(self.hasher(), self.S)
        self.M = _calculate_M(self.hasher, self.g, self.N, self.username, slt, self.A, ver_B, self.session_key)
        self.H_AMK = _H(self.hasher(), self.A, self.M, self.session_key)
        return self.M

    def verify_session(self, ver_H_AMK):
        """Verify session with verifier response H_AMK.
        @param ver_H_AMK Verifier evidence message.
        @return User/verifier H_AMK value on sucess, None if verification failed.
        """
        vs = (self.H_AMK == ver_H_AMK)
        if (vs):
            self.auth = True
        return self.H_AMK if vs else None

    def authenticated(self):
        """Check for successful authentication.
        @return True if session has been authenticated, False otherwise.
        """
        return self.auth


class Verifier:
    "SRP verifier (server) class."
    def __init__(self, hsf = DEFAULT_HASHER, gn = DEFAULT_GROUP):
        """Initialize verifier object.
        @param hsf Hash factory.
        @param gn Generator and safe prime group tuple.
        """
        self.hasher = hsf
        self.username = b''
        self.g = gn[0]
        self.N = gn[1]

        l = self.N.bit_length()
        self.k = _to_int(_H(self.hasher(), self.N, _pad(self.g, l)))

        self.b = 0
        self.B = 0
        self.S = 0
        self.M = b''
        self.H_AMK = b''
        self.session_key = b''
        self.auth = False

    def get_challenge(self, usn, slt, ver, usr_A, scs = DEFAULT_SECRETSIZE):
        """Start session and generate challenge for user, precalculating premaster secret and session key too.
        @param usn Username string.
        @param slt Salt value.
        @param ver Verification key.
        @param usr_A User public value.
        @param scs Byte size of secret private value.
        @return Verifier public value challenge on success, None otherwise.
        """
        self.username = usn
        # Safety check
        if usr_A % self.N == 0:
            return None

        l = self.N.bit_length()
        self.b = _to_int(_randombytes(scs))

        # B = k*ver + g^b
        self.B = (self.k * ver + pow(self.g, self.b, self.N)) % self.N

        # Precalculate scrambler, premaster key, session key and evidence messages.
        u = _to_int(_H(self.hasher(), _pad(usr_A, l), _pad(self.B, l)))
        # S = (A*(v^u))^b
        self.S = pow(usr_A * pow(ver, u, self.N), self.b, self.N)
        # Secret shared session key
        self.session_key = _H(self.hasher(), self.S)
        self.M = _calculate_M(self.hasher, self.g, self.N, usn, slt, usr_A, self.B, self.session_key)
        self.H_AMK = _H(self.hasher(), usr_A, self.M, self.session_key)
        return self.B

    def verify_session(self, usr_M):
        """Verify session with user response M.
        @param usr_M User evidence message.
        @return Verifier evidence message H_AMK on success, None otherwise.
        """
        vs = (self.M == usr_M)
        if (vs):
            self.auth = True
        return self.H_AMK if vs else None

    def authenticated(self):
        """Check for successful authentication.
        @return True if session has been authenticated, False otherwise.
        """
        return self.auth


#def _print_hex(b):
#    b = b if type(b) == bytes else _to_bytes(b)
#    for i in range(len(b)//16 + 1):
#        print(str.join(' ', ('%02x' % j for j in b[i*16:(i+1)*16])))

def _print_hex(b):
    b = b if type(b) == bytes else _to_bytes(b)
    for i in range(len(b)):
        if (i+1) % 32 == 0:
            sep = '\n'
        elif (i+1) % 4 == 0:
            sep = ' '
        else:
            sep = ''
        print(b[i].hex() + sep, end='')
    print()


if __name__ == '__main__':
    "Test module."

    # The scariest moment is always just before you start.
    class AuthException(Exception):
        pass

    # I took a test in Existentialism. I left all the answers blank and got 100.
    usr = User()
    ver = Verifier()

    I = 'username' # Hello, I love you - won't you tell me your name?
    P = 'password' # Methinks it is like a weasel.
    print("I = '{}', P = '{}'\n".format(I, P))

    # He just smiled and gave me a vegemite sandwich.
    print('- Create salted_verification_key(I, P)\n')
    s, v = salted_verification_key(I, P)

    print('* s =')
    _print_hex(s)
    print('* v =')
    _print_hex(v)

    # If you want to keep a secret, you must also hide it from yourself.
    print('<< User<->Verifier: I, s, v >>\n')

    print('- User: start_authentication(I, P)\n')
    A = usr.start_authentication(I, P)

    print('* User a =')
    _print_hex(usr.a)
    print('* User A =')
    _print_hex(A)

    # Give him a mask, and he will tell you the truth.
    print('<< User->Verifier: A >>\n')

    print('- Verifier: get_challenge(I, s, v, A)\n')
    B = ver.get_challenge(I, s, v, A)
    if B is None:
        # There are no good girls gone wrong - just bad girls found out.
        raise AuthException()

    print('* Verifier b =')
    _print_hex(ver.b)
    print('* Verifier B =')
    _print_hex(B)
    print('* Verifier S =')
    _print_hex(ver.S)

    # Say hello to my little friend.
    print('<< Verifier->User: B >>\n')

    print('- User: process_challenge(s, B)\n')
    M = usr.process_challenge(s, B)
    if M is None:
        # If a book about failures doesn't sell, is it a success?
        raise AuthException()

    print('* User M =')
    _print_hex(M)
    print('* User S =')
    _print_hex(usr.S)

    # You don't say?
    print('<< User->Verifier: M >>\n')

    print('- Verifier: verify_session(M)\n')
    H_AMK = ver.verify_session(M)
    if H_AMK is None:
        # A good friend will always stab you in the front.
        print('[ Authentication failed ]\n')
        raise AuthException()

    print('* Verifier M =')
    _print_hex(ver.M)
    print('* Verifier H_AMK =')
    _print_hex(H_AMK)

    # You're invisible now, you got no secrets to conceal.
    print('<< Verifier->User: H_AMK >>\n')

    print('- User: verify_session(H_AMK)\n')
    H_AMK = usr.verify_session(H_AMK)
    if H_AMK is None:
        # All you need in this life is ignorance and confidence; then success is sure.
        print('[ Authentication failed ]\n')
        raise AuthException()

    print('* User H_AMK =')
    _print_hex(H_AMK)

    # Two wrongs don't make a right, but they make a good excuse.
    assert usr.authenticated()
    assert ver.authenticated()

    # Three may keep a secret, if two of them are dead.
    print('[ Authentication success ]\n')

    print('* User session_key =')
    _print_hex(usr.session_key)
    print('* Verifier session_key =')
    _print_hex(ver.session_key)

    # I may not have gone where I intended to go, but I think I have ended up where I needed to be.
    print('END')
