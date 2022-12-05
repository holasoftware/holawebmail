/*
 * Construct an SRP object with a username,
 * password, and the bits identifying the 
 * group (1024 [default], 1536 or 2048 bits).
 */
var SRPClient = function (username, password, group, hashFnName) {
  
  // Verify presence of username.
  if (!username)
    throw 'Username cannot be empty.'
    
  // Store username/password.
  this.username = username;
  this.password = password;
  
  // Initialize hash function
  if (hashFnName){
    hashFnName = hashFnName.toLowerCase()
  } else {
    hashFnName = 'sha-1';
  }

  this.hash = SRPClient.hashFn[hashFnName];
  
  // Retrieve initialization values.
  var group = group || 1024;
  var initVal = SRPClient.initVals[group];

  this.nlen = initVal.N.length;
  
  // Set N and g from initialization values.
  this.N = new BigInteger(initVal.N, 16);
  this.g = new BigInteger(initVal.g, 16);
  
  // Pre-compute k from N and g.
  this.k = this.k();

  this.a = null;
  this.salt = null;
  this.A = null;
  this.B = null;
  this.S = null;
  this.K = null;
  this.M = null;
  this.H_AMK = null;

  this.auth = false;
};

SRPClient.prototype.startAuthentication = function(){
  this.a = this.getRandomEphemeral();
  this.A = this.calculateA(this.a);

  return this.a;
}


SRPClient.prototype.processChallenge = function(bHex, salt){
  this.B = new BigInteger(bHex, 16);

  this.salt = salt;

  // 4. The client and the server both calculate U.
  var U = this.calculateU(this.A, this.B);

  // 5. The client generates its premaster secret.
  this.S = this.calculateS(this.B, salt, U, this.a);
  this.K = this.calculateK(this.S);

  var mHex = this.calculateM_extended(salt, this.A, this.B, this.K);

  this.M = new BigInteger(mHex, 16);

  return mHex;
}

SRPClient.prototype.verifySession = function(ver_H_AMK){
    // Verify session with verifier response H_AMK.

    this.H_AMK = this.calculateM(this.A, this.M, this.K);
    if (this.H_AMK === ver_H_AMK) this.auth = true;

    return this.auth
}

/*
 * Implementation of an SRP client conforming
 * to the SRP protocol 6A (see RFC5054).
 */

/*
* Calculate k = H(N || g), which is used
* throughout various SRP calculations.
*/

SRPClient.prototype.k = function() {
    // Convert to hex values.
    var toHash = [
      this.N.toString(16),
      this.g.toString(16)
    ];

    // Return hash as a BigInteger.
    return this.paddedHash(toHash);
}

/*
* Calculate x = SHA1(s | SHA1(I | ":" | P))
*/
SRPClient.prototype.calculateX = function (saltHex) {
    // Verify presence of parameters.
    if (!saltHex) throw 'Missing parameter.'

    if (!this.username || !this.password)
      throw 'Username and password cannot be empty.';

    // Hash the concatenated username and password.
    var usernamePassword = this.username + ":" + this.password;
    var usernamePasswordHash = this.hash(usernamePassword);

    // Calculate the hash of salt + hash(username:password).
    var X = this.hashHex(saltHex + usernamePasswordHash);

    // Return X as a BigInteger.
    return new BigInteger(X, 16);
};

/*
* Calculate v = g^x % N
*/
SRPClient.prototype.calculateV = function(salt) {
    // Verify presence of parameters.
    if (!salt) throw 'Missing parameter.';

    // Get X from the salt value.
    var x = this.calculateX(salt);

    // Calculate and return the verifier.
    return this.g.modPow(x, this.N);
};

/*
* Calculate u = SHA1(PAD(A) | PAD(B)), which serves
* to prevent an attacker who learns a user's verifier
* from being able to authenticate as that user.
*/
SRPClient.prototype.calculateU = function(A, B) {
    // Verify presence of parameters.
    if (!A || !B) throw 'Missing parameter(s).';

    // Verify value of A and B.
    if (A.mod(this.N).toString() == '0' ||
        B.mod(this.N).toString() == '0')
      throw 'ABORT: illegal_parameter';

    // Convert A and B to hexadecimal.
    var toHash = [A.toString(16), B.toString(16)];

    // Return hash as a BigInteger.
    return this.paddedHash(toHash);
};

/*
* 2.5.4 Calculate the client's public value A = g^a % N,
* where a is a random number at least 256 bits in length.
*/
SRPClient.prototype.calculateA = function(a) {
    // Verify presence of parameter.
    if (!a) throw 'Missing parameter.';

    if (Math.ceil(a.bitLength() / 8) < 256/8)
      throw 'Client key length is less than 256 bits.'

    // Return A as a BigInteger.
    var A = this.g.modPow(a, this.N);

    if (A.mod(this.N).toString() == '0')
      throw 'ABORT: illegal_parameter';

    return A;
};

/*
* Calculate match M = H(A, B, K) or M = H(A, M, K)
*/
SRPClient.prototype.calculateM = function (A, B_or_M, K) {
    // Verify presence of parameters.
    if (!A || !B_or_M || !K)
      throw 'Missing parameter(s).';

    // Verify value of A and B.
    if (A.mod(this.N).toString() == '0' ||
        B_or_M.mod(this.N).toString() == '0')
      throw 'ABORT: illegal_parameter';

    var aHex = A.toString(16);
    var bHex = B_or_M.toString(16);

    var toHash = [aHex, bHex, K].join("");

    return this.hashHex(toHash);
};


SRPClient.prototype.calculateM_extended = function (s, A, B, K) {
    // Verify presence of parameters.
    if (!s || !A || !B || !K)
      throw 'Missing parameter(s).';

    // Verify value of A and B.
    if (A.mod(this.N).toString() == '0' ||
        B.mod(this.N).toString() == '0')
      throw 'ABORT: illegal_parameter';

    var aHex = A.toString(16);
    var bHex = B.toString(16);

    var H_N = this.hashHex(this.N.toString(16));
    var H_g = this.hashHex(this.g.toString(16));
    var H_I = this.hash(this.username);

    var H_xor = this.hexXor(H_N, H_g);

    var toHash = [H_xor, H_I, s, aHex, bHex, K].join("");

    return this.hashHex(toHash);
};

SRPClient.prototype.hexXor = function(a, b) {
    var str = '';
    for (var i = 0; i < a.length; i += 2) {
      var xor = parseInt(a.substr(i, 2), 16) ^ parseInt(b.substr(i, 2), 16)
      xor = xor.toString(16);
      str += (xor.length == 1) ? ("0" + xor) : xor
    }
    return str;
};

/*
* Calculate the client's premaster secret 
* S = (B - (k * g^x)) ^ (a + (u * x)) % N
*/
SRPClient.prototype.calculateS = function(B, salt, uu, aa) {
    // Verify presence of parameters.
    if (!B || !salt || !uu || !aa)
      throw 'Missing parameters.';

    // Verify value of B.
    if (B.mod(this.N).toString() == '0')
      throw 'ABORT: illegal_parameter';
      
    // Calculate X from the salt.
    var x = this.calculateX(salt);

    // Calculate bx = g^x % N
    var bx = this.g.modPow(x, this.N);

    // Calculate ((B + N * k) - k * bx) % N
    var btmp = B.add(this.N.multiply(this.k))
    .subtract(bx.multiply(this.k)).mod(this.N);

    // Finish calculation of the premaster secret.
    return btmp.modPow(x.multiply(uu).add(aa), this.N);
};

SRPClient.prototype.calculateK = function (S) {
    return this.hashHex(S.toString(16));
};

/*
* Helper functions for random number
* generation and format conversion.
*/

/* Generate a random big integer */
SRPClient.prototype.getRandomHexNumberMinBits = function(minBits){
    var n = Math.ceil(minBits / 8);

    var randomHex = Number(Math.floor(CryptoRand.rand()*255) + 1 ).toString(16) +  CryptoRand.random1byteHex(n);

    return randomHex;
};

SRPClient.prototype.isInvalidEphemeral = function(a) {
    return (this.g.modPow(a, this.N) == 0 || a.bitLength() < 256);
};

// a should be 256 bit in length minimum
SRPClient.prototype.getRandomEphemeral = function() {
    var a;

    do {
      a = new BigInteger(this.getRandomHexNumberMinBits(256), 16);
    } while(this.isInvalidEphemeral(a));

    return a;
};

// generate random salt
SRPClient.prototype.randomHexSalt = function(opionalServerSalt) {
    var s = null;

    /* jshint ignore:start */
    s = CryptoRand.random1byteHex(16);
    /* jshint ignore:end */

    // if you invoke without passing the string parameter the '+' operator uses 'undefined' so no nullpointer risk here
    var ss = this.hash((new Date())+':'+opionalServerSalt+':'+s);
    return ss;
};


/*
* Helper functions for hasing/padding.
*/

/*
* SHA1 hashing function with padding: input 
* is prefixed with 0 to meet N hex width.
*/
SRPClient.prototype.paddedHash = function (array) {
    var nlen = this.nlen;

    var toHash = '';

    for (var i = 0; i < array.length; i++) {
     toHash += this.nZeros(nlen - array[i].length) + array[i];
    }

    var hash = new BigInteger(this.hashHex(toHash), 16);

    return hash.mod(this.N);
};

/*
* Hexadecimal hashing function.
*/
// 
SRPClient.prototype.hashHex = function (str) {
 return this.hash(this.hex2a(str));
};

/*
* Hex to string conversion.
*/
SRPClient.prototype.hex2a = function(hex) {
    var str = '';
    if (hex.length % 2 != 0) hex = '0' + hex;

    for (var i = 0; i < hex.length; i += 2)
      str += String.fromCharCode(parseInt(hex.substr(i, 2), 16));
    return str;
};

/* Return a string with N zeros. */
SRPClient.prototype.nZeros = function(n) {
    if(n < 1) return '';
    var t = this.nZeros(n >> 1);

    return ((n & 1) == 0) ?
      t + t : t + t + '0';
};

/*
* Server-side SRP functions. These should not
* be used on the client except for debugging.
*/

/* Calculate the server's public value B. */
SRPClient.prototype.calculateB = function(b, v) {
    // Verify presence of parameters.
    if (!b || !v) throw 'Missing parameters.';

    var bb = this.g.modPow(b, this.N);
    var B = bb.add(v.multiply(this.k)).mod(this.N);

    return B;
};

/* Calculate the server's premaster secret */
SRPClient.prototype.calculateServerS = function(A, v, u, B) {
    // Verify presence of parameters.
    if (!A || !v || !u || !B)
      throw 'Missing parameters.';

    // Verify value of A and B.
    if (A.mod(this.N).toString() == '0' ||
        B.mod(this.N).toString() == '0')
      throw 'ABORT: illegal_parameter';

    return v.modPow(u, this.N).multiply(A)
           .mod(this.N).modPow(B, this.N);
};

SRPClient.hashFn = {
    'sha-1': SHA1,
    'sha-256': SHA256,
    'md5': MD5
}

/*
* SRP group parameters, composed of N (hexadecimal
* prime value) and g (decimal group generator).
* See http://tools.ietf.org/html/rfc5054#appendix-A
*/
SRPClient.initVals = {
    1024: {
      N: 'EEAF0AB9ADB38DD69C33F80AFA8FC5E86072618775FF3C0B9EA2314C' +
         '9C256576D674DF7496EA81D3383B4813D692C6E0E0D5D8E250B98BE4' +
         '8E495C1D6089DAD15DC7D7B46154D6B6CE8EF4AD69B15D4982559B29' +
         '7BCF1885C529F566660E57EC68EDBC3C05726CC02FD4CBF4976EAA9A' +
         'FD5138FE8376435B9FC61D2FC0EB06E3',
      g: '2'

    },

    1536: {
      N: '9DEF3CAFB939277AB1F12A8617A47BBBDBA51DF499AC4C80BEEEA961' +
         '4B19CC4D5F4F5F556E27CBDE51C6A94BE4607A291558903BA0D0F843' +
         '80B655BB9A22E8DCDF028A7CEC67F0D08134B1C8B97989149B609E0B' +
         'E3BAB63D47548381DBC5B1FC764E3F4B53DD9DA1158BFD3E2B9C8CF5' +
         '6EDF019539349627DB2FD53D24B7C48665772E437D6C7F8CE442734A' +
         'F7CCB7AE837C264AE3A9BEB87F8A2FE9B8B5292E5A021FFF5E91479E' +
         '8CE7A28C2442C6F315180F93499A234DCF76E3FED135F9BB',
      g: '2'
    },

    2048: {
      N: 'AC6BDB41324A9A9BF166DE5E1389582FAF72B6651987EE07FC319294' +              
         '3DB56050A37329CBB4A099ED8193E0757767A13DD52312AB4B03310D' +
         'CD7F48A9DA04FD50E8083969EDB767B0CF6095179A163AB3661A05FB' +
         'D5FAAAE82918A9962F0B93B855F97993EC975EEAA80D740ADBF4FF74' +
         '7359D041D5C33EA71D281E446B14773BCA97B43A23FB801676BD207A' +
         '436C6481F1D2B9078717461A5B9D32E688F87748544523B524B0D57D' +
         '5EA77A2775D2ECFA032CFBDBF52FB3786160279004E57AE6AF874E73' +
         '03CE53299CCC041C7BC308D82A5698F3A8D0C38271AE35F8E9DBFBB6' +
         '94B5C803D89F7AE435DE236D525F54759B65E372FCD68EF20FA7111F' +
         '9E4AFF73',
      g: '2'
    },

    3072: {
      N: 'FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E08' +
         '8A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B' +
         '302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9' +
         'A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE6' +
         '49286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8' +
         'FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D' +
         '670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C' +
         '180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718' +
         '3995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D' +
         '04507A33A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7D' +
         'B3970F85A6E1E4C7ABF5AE8CDB0933D71E8C94E04A25619DCEE3D226' +
         '1AD2EE6BF12FFA06D98A0864D87602733EC86A64521F2B18177B200C' +
         'BBE117577A615D6C770988C0BAD946E208E24FA074E5AB3143DB5BFC' +
         'E0FD108E4B82D120A93AD2CAFFFFFFFFFFFFFFFF',
      g: '5'
    },

    4096: {
      N: 'FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E08' +
         '8A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B' +
         '302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9' +
         'A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE6' +
         '49286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8' +
         'FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D' +
         '670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C' +
         '180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718' +
         '3995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D' +
         '04507A33A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7D' +
         'B3970F85A6E1E4C7ABF5AE8CDB0933D71E8C94E04A25619DCEE3D226' +
         '1AD2EE6BF12FFA06D98A0864D87602733EC86A64521F2B18177B200C' +
         'BBE117577A615D6C770988C0BAD946E208E24FA074E5AB3143DB5BFC' +
         'E0FD108E4B82D120A92108011A723C12A787E6D788719A10BDBA5B26' +
         '99C327186AF4E23C1A946834B6150BDA2583E9CA2AD44CE8DBBBC2DB' +
         '04DE8EF92E8EFC141FBECAA6287C59474E6BC05D99B2964FA090C3A2' +
         '233BA186515BE7ED1F612970CEE2D7AFB81BDD762170481CD0069127' +
         'D5B05AA993B4EA988D8FDDC186FFB7DC90A6C08F4DF435C934063199' +
         'FFFFFFFFFFFFFFFF',
      g: '5'
    },

    6144: {
      N: 'FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E08' +
         '8A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B' +
         '302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9' +
         'A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE6' +
         '49286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8' +
         'FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D' +
         '670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C' +
         '180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718' +
         '3995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D' +
         '04507A33A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7D' +
         'B3970F85A6E1E4C7ABF5AE8CDB0933D71E8C94E04A25619DCEE3D226' +
         '1AD2EE6BF12FFA06D98A0864D87602733EC86A64521F2B18177B200C' +
         'BBE117577A615D6C770988C0BAD946E208E24FA074E5AB3143DB5BFC' +
         'E0FD108E4B82D120A92108011A723C12A787E6D788719A10BDBA5B26' +
         '99C327186AF4E23C1A946834B6150BDA2583E9CA2AD44CE8DBBBC2DB' +
         '04DE8EF92E8EFC141FBECAA6287C59474E6BC05D99B2964FA090C3A2' +
         '233BA186515BE7ED1F612970CEE2D7AFB81BDD762170481CD0069127' +
         'D5B05AA993B4EA988D8FDDC186FFB7DC90A6C08F4DF435C934028492' +
         '36C3FAB4D27C7026C1D4DCB2602646DEC9751E763DBA37BDF8FF9406' +
         'AD9E530EE5DB382F413001AEB06A53ED9027D831179727B0865A8918' +
         'DA3EDBEBCF9B14ED44CE6CBACED4BB1BDB7F1447E6CC254B33205151' +
         '2BD7AF426FB8F401378CD2BF5983CA01C64B92ECF032EA15D1721D03' +
         'F482D7CE6E74FEF6D55E702F46980C82B5A84031900B1C9E59E7C97F' +
         'BEC7E8F323A97A7E36CC88BE0F1D45B7FF585AC54BD407B22B4154AA' +
         'CC8F6D7EBF48E1D814CC5ED20F8037E0A79715EEF29BE32806A1D58B' +
         'B7C5DA76F550AA3D8A1FBFF0EB19CCB1A313D55CDA56C9EC2EF29632' +
         '387FE8D76E3C0468043E8F663F4860EE12BF2D5B0B7474D6E694F91E' +
         '6DCC4024FFFFFFFFFFFFFFFF',
      g: '5'
    },

    8192: {
      N:'FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E08' +
        '8A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B' +
        '302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9' +
        'A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE6' +
        '49286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8' +
        'FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D' +
        '670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C' +
        '180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718' +
        '3995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D' +
        '04507A33A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7D' +
        'B3970F85A6E1E4C7ABF5AE8CDB0933D71E8C94E04A25619DCEE3D226' +
        '1AD2EE6BF12FFA06D98A0864D87602733EC86A64521F2B18177B200C' +
        'BBE117577A615D6C770988C0BAD946E208E24FA074E5AB3143DB5BFC' +
        'E0FD108E4B82D120A92108011A723C12A787E6D788719A10BDBA5B26' +
        '99C327186AF4E23C1A946834B6150BDA2583E9CA2AD44CE8DBBBC2DB' +
        '04DE8EF92E8EFC141FBECAA6287C59474E6BC05D99B2964FA090C3A2' +
        '233BA186515BE7ED1F612970CEE2D7AFB81BDD762170481CD0069127' +
        'D5B05AA993B4EA988D8FDDC186FFB7DC90A6C08F4DF435C934028492' +
        '36C3FAB4D27C7026C1D4DCB2602646DEC9751E763DBA37BDF8FF9406' +
        'AD9E530EE5DB382F413001AEB06A53ED9027D831179727B0865A8918' +
        'DA3EDBEBCF9B14ED44CE6CBACED4BB1BDB7F1447E6CC254B33205151' +
        '2BD7AF426FB8F401378CD2BF5983CA01C64B92ECF032EA15D1721D03' +
        'F482D7CE6E74FEF6D55E702F46980C82B5A84031900B1C9E59E7C97F' +
        'BEC7E8F323A97A7E36CC88BE0F1D45B7FF585AC54BD407B22B4154AA' +
        'CC8F6D7EBF48E1D814CC5ED20F8037E0A79715EEF29BE32806A1D58B' +
        'B7C5DA76F550AA3D8A1FBFF0EB19CCB1A313D55CDA56C9EC2EF29632' +
        '387FE8D76E3C0468043E8F663F4860EE12BF2D5B0B7474D6E694F91E' +
        '6DBE115974A3926F12FEE5E438777CB6A932DF8CD8BEC4D073B931BA' +
        '3BC832B68D9DD300741FA7BF8AFC47ED2576F6936BA424663AAB639C' +
        '5AE4F5683423B4742BF1C978238F16CBE39D652DE3FDB8BEFC848AD9' +
        '22222E04A4037C0713EB57A81A23F0C73473FC646CEA306B4BCBC886' +
        '2F8385DDFA9D4B7FA2C087E879683303ED5BDD3A062B3CF5B3A278A6' +
        '6D2A13F83F44F82DDF310EE074AB6A364597E899A0255DC164F31CC5' +
        '0846851DF9AB48195DED7EA1B1D510BD7EE74D73FAF36BC31ECFA268' +
        '359046F4EB879F924009438B481C6CD7889A002ED5EE382BC9190DA6' +
        'FC026E479558E4475677E9AA9E3050E2765694DFC81F56E880B96E71' +
        '60C980DD98EDD3DFFFFFFFFFFFFFFFFF',
      g: '13'  /* 19 decimal */
    }
};


