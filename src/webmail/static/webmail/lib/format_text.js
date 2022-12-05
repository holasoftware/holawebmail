(function(global){

    function format(text, context) {
      context = context || {};

      return String(text).split("%%").map(function(textPart){
            return textPart.replace(/%\((\w+)\)s/g, replaceTextParam(context, text));
      }).join("%");
    };

    var NoContextParamError = new Error("No context param");

    function replaceTextParam(context, text){
      return function (tag, name) {
        if (!context.hasOwnProperty(name)) {
          throw new Error("No context param '" + name + "' in formated text: " + text);
        }

        if (typeof context[name] == 'function') {
          return context[name]();
        }

        return context[name];
      }
    }

    global.format = format;
})(this);
