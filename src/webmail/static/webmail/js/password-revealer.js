/**
 * password-revealer.js
 * Easily reveal/hide passwords in input fields.
 *
 * @version 1.1.1
 * @author Diéssica Gurskas <http://github.com/diessica>
 * @license MIT
 */

/**
 * @param {String|HTMLElement} input
 * @param {Object} options
 */
var PasswordRevealer = function(input, toggleElement, options){
  const defaults = {
      onTriggerAction: null,
      eventListener: 'click'
  }

  if (!input) {
    throw new Error('Missing input HTML element')
  }

  if (typeof input === 'string') {
    input = document.querySelector(input)
  }

  if (input.nodeName !== 'INPUT') {
    throw new Error('First argument (input) must be an input element')
  }

  this.input = input;

  if (!toggleElement) {
    throw new Error('Missing toggle HTML element')
  }

  if (typeof toggleElement === 'string') {
    toggleElement = document.querySelector(toggleElement)
  }

  this.toggleElement = toggleElement;

  if (typeof options === 'object') {
    options = Object.assign({}, defaults, options)
  } else {
    options = defaults
  }

  this.onTriggerAction = options.onTriggerAction;
  this.eventListener = options.eventListener;

  this.isRevealed = input.type !== 'password';
}

PasswordRevealer.prototype.show = function(){
    this.input.type = 'text'
    this.isRevealed = true
}

PasswordRevealer.prototype.hide = function(){
    this.input.type = 'password';
    this.isRevealed = false;
}

PasswordRevealer.prototype.toggle = function(){
    if (this.isRevealed) {
      this.hide()
    } else {
      this.show()
    }
}

PasswordRevealer.prototype.init = function(){
    var self = this;

    this.toggleElement.addEventListener(this.eventListener, function(e){
        e.preventDefault();

        self.toggle();

        if (self.onTriggerAction)
            self.onTriggerAction(self.isRevealed, self.toggleElement);
    });
}
