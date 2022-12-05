;(function (root, factory) {
  if (typeof exports === 'object' && typeof module === 'object') {
    module.exports = factory();
  } else if(typeof define === 'function' && define.amd) {
    define([], factory);
  } else if(typeof exports === 'object') {
    exports['notifier'] = factory();
  } else {
    root['notifier'] = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  var _id = 0;
  var numNotifications = 0;

  var createHTMLElement = function(elem, attrs) {
    var el = document.createElement(elem);
    for (var prop in attrs) {
      el.setAttribute(prop, attrs[prop]);
    }
    return el;
  };

  var transitionEndEventName = (function () {
    var el = document.createElement('_fake');
    var transitions = {
        MozTransition: 'transitionend',
        OTransition: 'oTransitionEnd',
        WebkitTransition: 'webkitTransitionEnd',
        transition: 'transitionend',
    };
    var t;
    for (t in transitions) {
        if (el.style[t] !== undefined) {
            return transitions[t];
        }
    }
    // No supported animation end event.
    return null;
  })();

  var createNotifierListContainer = function() {
    var container = createHTMLElement('div', {class: 'notification-list', id: 'notification-list'});
    document.body.appendChild(container);

    return container;
  };

  var container = null;

  var buildNotificationCard = function(ntfId, title, msg, type, icon, dismissible){
    var ntf       = createHTMLElement('div', {id: ntfId, class: 'notification'}),
        ntfBody   = createHTMLElement('div', {class: 'notification-body'}),
        ntfTextMessage   = createHTMLElement('div', {class: 'notification-text-message'});

    if (type) {
        ntf.className += ' notification-type-' + type
    }

    if (dismissible) {
        var ntfClose  = createHTMLElement('button',{class: 'notification-close-btn', type: 'button'});
        ntfClose.innerHTML = '&times;';

        ntf.appendChild(ntfClose);

        ntfClose.addEventListener('click', function() {
          hide(ntfId);
        });
    }

    if (icon) {
      var ntfImg    = createHTMLElement('div', {class: 'notification-img'}),
          img       = createHTMLElement('img', {src: icon});

      ntfImg.appendChild(img);
      ntfBody.appendChild(ntfImg);

      ntf.className += ' notification-has-icon';

      // TODO: Revisar
      // ntfImg.style.height = ntfImg.parentNode.offsetHeight + 'px' || null;
    }

    ntf.appendChild(ntfBody);

    if (title){
      var ntfTitle  = createHTMLElement('h2',  {class: 'notification-title'});
      ntfTitle.innerHTML = title;

      ntfBody.appendChild(ntfTitle);
    }

    ntfTextMessage.innerHTML = msg;
    ntfBody.appendChild(ntfTextMessage);

    numNotifications += 1;
    return ntf;
  }

  var removeNotification = function(notification){
    console.log("aquiiiiiiiiiiiiiI");
    notification.parentNode.removeChild(notification);

    numNotifications -= 1;

    console.log("numNotifications", numNotifications)

    if (numNotifications === 0){
        container.parentNode.removeChild(container);
        container = null;
    }
  }

  var show = function(title, msg, type, icon, dismissible, timeout) {
    var ntfId = 'notification-' + _id;
    _id += 1;

    var ntf = buildNotificationCard(ntfId, title, msg, type, icon, dismissible);

    if (container === null){
        container = createNotifierListContainer()
    }
    container.appendChild(ntf);

    setTimeout(function() {
      ntf.className += ' notification-shown';
    }, 100);

    if (timeout) {
      setTimeout(function() {
        hide(ntfId);
      }, timeout);
    }

    return ntfId;
  };

  var hide = function(ntfId) {
    var notification = document.getElementById(ntfId);

    if (notification) {
      notification.className = notification.className.replace(' notification-shown', '');

      if (transitionEndEventName){
        var handleEvent

        notification.addEventListener(transitionEndEventName, (handleEvent = function (event) {
            if (event.target === notification) {
                notification.removeEventListener(transitionEndEventName, handleEvent);
                removeNotification(notification);
            }
        }));
      } else {
          setTimeout(function() {
            removeNotification(notification);
          }, 600);
      }

      return true;

    } else {
      return false;
    }
  };


  return {
    show: show,
    hide: hide
  };
}));
