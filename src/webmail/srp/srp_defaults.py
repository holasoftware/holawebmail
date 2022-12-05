"""@package py3srp
  Secure Remote Password (SRP-6a) protocol implementation in pure Python3.

  SRP module definitions.

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

import hashlib
from .srp_rfc5054 import gN

## Default hash factory
#DEFAULT_HASHER = hashlib.sha512
DEFAULT_HASHER = hashlib.sha256

DEFAULT_BIT_GROUP_NUMBER = 3072
## Default gN group (generator, safe prime) tuple
DEFAULT_GROUP = gN[DEFAULT_BIT_GROUP_NUMBER]

## Default salt size
DEFAULT_SALTSIZE = 32

## Default secret (peer private value) size
DEFAULT_SECRETSIZE = 256

## Default username-password separator
DEFAULT_SEPARATOR = b':'

## Default byteorder for integer storage
DEFAULT_BYTEORDER = 'big'

## Default string encoding
DEFAULT_ENCODING = 'utf-8'

## Default integer number radix
DEFAULT_RADIX = 16
