/*
 * "random.js" requires https://github.com/rubycon/isaac.js/blob/master/isaac.js
 * Copyright (c) 2014 Simon Massey
 * http://www.apache.org/licenses/LICENSE-2.0
 */
/*
This module tries to use window.crypto random number generator which is available 
in modern browsers. If it cannot find that then it falls back to using an isaac 
random number generator which is seeded by Math.random and any cookies. To improve
security whcn using isaac it will skip forward until some time has passed. This will
make the amount of randoms skipped determined by hardware/browser/load. You can attach
the skip method to html input boxes with:
random16byteHex.advance(Math.floor(event.keyCode/4));
which will further advance the stream an unpredictable amount. If the browser
has built in crypto randoms the advance method with do nothing.
Do not add to the password box to leak any info about the password to the outside world.
*/
var CryptoRand = (function() {

  function isWebCryptoAPI() {
    if (typeof(window) != 'undefined' && window.crypto && window.crypto.getRandomValues) {
      return true;
    }
    else if (typeof(window) != 'undefined' && window.msCrypto && window.msCrypto.getRandomValues) {
      return true;
    } else {
      return false;
    }
  };

  var crypto = isWebCryptoAPI();

  function seedIsaac() {
    //console.log("isWebCryptoAPI:"+crypto);
    if( crypto ) return false;
    var value = +(new Date())+':'+Math.random();
    if( typeof(window) != 'undefined' && window.cookie) {
      value += document.cookie;
    }

    isaac.seed(SHA256(value));
    return true;
  }

  var seeded = seedIsaac();

  function random1byteHex(n) {
    n = n || 1;

    var randomBytes;

    if( crypto ) {
      var acrypto = window.crypto || window.msCrypto;
      randomBytes = new Uint8Array(n);
      acrypto.getRandomValues(randomBytes);
    } else {
        // skip forward an unpredictable amount
        var now = +(new Date());
        var t = now % 50;
        isaac.prng(1+t);

        // grab some words
        randomBytes = new Array();
        for (var i = 0; i < n; i++) {
            randomBytes.push(Math.floor(isaac.random()*256));
        }
    }

    var string = '';
    var hex;
    
    for( var i=0; i<n; i++ ) {
      var uint8 = randomBytes[i];

      hex = uint8.toString(16);
      if (hex.length === 1) hex = '0' + hex;

      string = string + hex;
    }
    //console.log(string);
    return string;
  };
  	
  function rand() {
    if( crypto ) {
      var acrypto = window.crypto || window.msCrypto;
      var randomWords = new Uint32Array(1);
      acrypto.getRandomValues(randomWords);

      return 0.5 + randomWords[0] * 2.3283064365386963e-10; // 2^-32
    } else {
      return isaac.random()
    }
  }

  /**
  Run this within onkeyup of html inputs so that user typing makes the random numbers more random:
  random16byteHex.advance(Math.floor(event.keyCode/4));
  */
  function advance(ms) {
    if( !crypto ) {
      var start = +(new Date());
      var end = start + ms;
      var now = +(new Date());
      while( now < end ) {
          var t = now % 5;
          isaac.prng(1+t);
          now = +(new Date());
      }
    }
  }
  
  return {
    'rand': rand,
    'random1byteHex' : random1byteHex,
    'isWebCryptoAPI' : crypto,
    'advance' : advance 
  };
})();

// if using isaac in a browser without secure random numbers spend 0.1s advancing the random stream
var isaacAlgorithmAdvance = 100;

// optional override during unit tests
if( typeof test_isaacAlgorithmAdvance != 'undefined' ) {
	isaacAlgorithmAdvance = test_isaacAlgorithmAdvance;
}

CryptoRand.advance(isaacAlgorithmAdvance);
