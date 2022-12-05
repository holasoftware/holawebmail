/*
 *
 * Inspired by:
 *   JavaScript Templates
 *     https://github.com/blueimp/JavaScript-Templates
 *
 *   Underscore template engine
 *
 */

/* global define */

;(function (global) {
    'use strict'

    // Certain characters need to be escaped so that they can be put into a
    // string literal.
    var ESPECIAL_CHARS_IN_LITERAL = {
        "'": "'",
        '\\': '\\',
        '\r': 'r',
        '\n': 'n',
        '\u2028': 'u2028',
        '\u2029': 'u2029'
    };

    var ESPECIAL_CHARS_IN_LITERAL_RE = /\\|'|\r|\n|\u2028|\u2029/g;

    var escapeChar = function(match) {
        return '\\' + ESPECIAL_CHARS_IN_LITERAL[match];
    };

    var ENCODE_ENTITY_RE = /[<>&"'`\x00]/g;
    var encodeEntityMap = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '`': '&#x60;'
    };

    var EVALUATE_RE = '<%([\\s\\S]+?)%>';
    var INTERPOLATE_RE = '<%=([\\s\\S]+?)%>';
    var ESCAPE_RE = '<%-([\\s\\S]+?)%>';

    // Combine delimiters into one regular expression via alternation.
    var matcher = RegExp([ESCAPE_RE, INTERPOLATE_RE, EVALUATE_RE].join('|') + '|$', 'g');


    // By default, Underscore uses ERB-style template delimiters, change the
    // following template settings to use alternative delimiters.

    var tmpl = function (text, data) {
        var fn;

        if (typeof tmpl.cache[text] === "undefined") {
            tmpl.cache[text] = tmpl.compile(text);
        }

        fn = tmpl.cache[text]; 

        return typeof data === "undefined" ? fn: fn(data);
    }

    tmpl.encodeEntity = function (s) {
        return (s == null ? '' : '' + s).replace(ENCODE_ENTITY_RE, function (c) {
            return encodeEntityMap[c] || ''
        })
    }

    tmpl.compile = function(text){
        // Compile the template source, escaping string literals appropriately.
        var index = 0;
        var source = "__p+='";
        text.replace(matcher, function(match, escape, interpolate, evaluate, offset) {
            source += text.slice(index, offset).replace(ESPECIAL_CHARS_IN_LITERAL_RE, escapeChar);
            index = offset + match.length;

            if (escape) {
                source += "'+\n((__t=(" + escape + "))==null?'':tmpl.encodeEntity(__t))+\n'";
            } else if (interpolate) {
                source += "'+\n((__t=(" + interpolate + "))==null?'':__t)+\n'";
            } else if (evaluate) {
                source += "';\n" + evaluate + "\n__p+='";
            }

            // Adobe VMs need the match returned to produce the correct offset.
            return match;
        });
        source += "';\n";

        // If a variable is not specified, place data values in local scope.
        if (!tmpl.arg) source = 'with(o||{}){\n' + source + '}\n';

        source = "var __t, __p='',\n  " +
            "print=function(s,e){__p+=e?(s==null?'':s):tmpl.encodeEntity(s);},\n  " + 
            "include=function(s,d){__p+=tmpl(s,d);};\n"  +
            source + 'return __p;\n';

        var render;
        try {
            render = new Function(tmpl.arg || 'o', '_', source);
        } catch (e) {
            e.source = source;
            throw e;
        }

        var fn = function(data) {
            return render.call(this, data);
        };

        // Provide the compiled source as a convenience for precompilation.
        var argument = tmpl.arg || 'o';
        fn.source = 'function(' + argument + '){\n' + source + '}';

        return fn;
    };


    tmpl.cache = {};
    tmpl.load = function (id, data) {
        return tmpl(document.getElementById(id).innerHTML, data);
    };

    tmpl.arg = 'o';


    if (typeof define === 'function' && define.amd) {
        define(function () {
            return tmpl;
        })
    } else if (typeof module === 'object' && module.exports) {
        module.exports = tmpl;
    } else {
        global.tmpl = tmpl;
    }
})(this)

