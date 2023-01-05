(function(global,undefined){

    var FORM_ERROR_CODE = "form_errors";

    var $global = $(global);

    function _(text){
        if (i18n && i18n.hasOwnProperty(text))
            return i18n[text];

        return text;
    }

    // TODO: Ofrecer validación
    function Form(el, actionUrl){
        this.$form = $(el);
        this.actionUrl = actionUrl || this.$form.attr("action") || window.location.href;
    }

    Form.prototype._getInputElement = function(fieldName){
        return this.$form.find("[name="+fieldName+"]");
    }

    Form.prototype.showFieldError = function(fieldName, msg){
        this._getInputElement(fieldName).parent().after("<p class='form-field-error'>"+msg+"</p>")
    }

    Form.prototype.fieldValue = function(fieldName, value){
        var $input = this._getInputElement(fieldName);

        if (value === undefined){
            return $input.val();
        } else {
            $input.val(value);
        }
    }

    Form.prototype.showError = function(msg){
        this.$form.find(".form-error").html(msg);
    }

    Form.prototype.clearErrors = function(msg){
        this.$form.find(".form-error").empty();
        this.$form.find(".form-field-error").remove()
    }

    Form.prototype.onSubmit = function(cb){
        var self = this;

        this.$form.on('submit', function(e) {
            e.preventDefault();

            cb.bind(self)(e);
        });
    }

    Form.prototype.send = function(callback, errback){
        var self = this;

        this.clearErrors();
        $.post(this.actionUrl, this.$form.serialize(), function(response) {
            if (response.ok){
                callback(response.data);
            } else {
                if (response.error_code === FORM_ERROR_CODE){
                    // TODO: Mostrar errores generales
                    Object.keys(response.error_data).forEach(function(fieldName){
                        response.error_data[fieldName].forEach(function(errorMessage){
                            self.showFieldError(fieldName, errorMessage)
                        });
                    });
                } else {
                    if (errback) errback(response)
                }
            }
            cb.bind(this)(e);
        }, "json");
    }

    function reverse_url(viewname, viewArgs){
        var patternFormat = URL_PATTERNS_STRING_FORMATS[viewname];

        if (!patternFormat) throw new Error("View name does not exist: " + viewname);
        var url = "/" + format(patternFormat, viewArgs);

        if (viewArgs === undefined || (viewArgs.mbox === undefined && MAILBOX_ID !== null)){
            url += "?mbox=" + MAILBOX_ID;
        }
        return url;
    }

    function reverse_absolute_url(viewname, viewArgs){
        return window.location.protocol + "//" + window.location.host + reverse_url(viewname, viewArgs);
    }

    function import_message(mbox, contactId, subject, content, attachments, callback, errback){
        // if (mbox === null) mbox = MAILBOX_ID;

        var message = serializeMessage(subject, content, attachments);
        var xhr = new XMLHttpRequest();

        xhr.onload = function(evt) {
            if(xhr.status == 200){
                // Fire the success/error handlers with the returned JSON
                var data = JSON.parse(xhr.responseText);
                if(data.ok) {
                    if (callback) callback(data);
                }
                else {
                    if (errback) errback(data);
                }
            } else {
                errback();
            }
        };

        xhr.open('POST', reverse_url("import_message", {
            "contact_id": contactId,
            "mbox": mbox
        }), true);            
        xhr.setRequestHeader("X-CSRFToken", CSRF_MIDDLEWARE_TOKEN);
        xhr.send(message);
    }

    function get_partial_template(template_name, context, callback, errback){
        $.post(reverse_url("partial_template"), {
            "csrfmiddlewaretoken": CSRF_MIDDLEWARE_TOKEN,
            "template_name": template_name,
            "context": JSON.stringify(context)
        }, function (response) {
            if (response.ok) {
                var html = response.data.html;
                callback(html);
            } else {
                // TODO: Notificar que algo salio mal
                errback(response);
            }
        });
    }

    function get_partial_templates_list(){
        var errback, callback;

        var i = 0;

        var args = Array.prototype.slice.call(arguments);

        if (args.length % 2 === 0){
            errback = args.pop();
            callback = args.pop();
        } else {
            errback = null;
            callback = args.pop();
        }

        var num_args = args.length;

        var html_list = [];

        var temp_callback = function(html){
            html_list.push(html);

            i += 2;
            if (i === num_args) {
                callback(html_list);
            } else {
                get_partial_template(args[i], args[i+1], temp_callback);
            }
        }

        get_partial_template(args[0], args[1], temp_callback, errback);
    }

    function show_notification(notification_type, message){
        var html = '<div style="margin-bottom:5px" class="alert alert-' + notification_type + ' alert-dismissible fade show" role="alert"><button type="button" class="close" data-dismiss="alert" aria-label="close">×</button> ' + message + '</div>';
        $("#content-area").prepend(html);
    }

    function show_success(message){
        return show_notification("success", message)
    }

    function show_danger(message){
        return show_notification("danger", message)
    }

    function show_warning(message){
        return show_notification("warning", message)
    }

    global.reverse_url = reverse_url;
    global.reverse_absolute_url = reverse_absolute_url;
    global.import_message = import_message;
    global.get_partial_template = get_partial_template;
    global.get_partial_templates_list = get_partial_templates_list;
    global.show_notification = show_notification;
    global.show_success = show_success;
    global.show_danger = show_danger;
    global.show_warning = show_warning;
    global._ = _;
    global.Form = Form;
    global.FORM_ERROR_CODE = FORM_ERROR_CODE;


    var PAGE_INITIALIZER = global.PAGE_INITIALIZER;

    PAGE_INITIALIZER["compose"] = compose_page_init;
    PAGE_INITIALIZER["folder"] = folder_page_init;
    PAGE_INITIALIZER["message"] = message_page_init;


    function init_page(page_name, data){
        if (PAGE_INITIALIZER[page_name] !== undefined ){
            if (data === undefined) data = null;

            PAGE_INITIALIZER[page_name](data);
        }

    }

    global.init_page = init_page;

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }


    /* Contact Info:
        - contactId
        - displayedName
        - email
        - createdAt
        - updatedAt
    */


    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", CSRF_MIDDLEWARE_TOKEN);
            }
        }
    });

    $(function(){
        var $webmail = $("#webmail");
        
        var $contentArea = $webmail.find("#content-area");

        var $userProfileLink = $("#user-profile");
        var $userProfileDropdownMenu = $userProfileLink.find("> .dropdown")
        $userProfileDropdownMenu.inMovement = false;

        $userProfileLink.hoverIntent( function(){
            if ($userProfileDropdownMenu.inMovement) return;

            $userProfileDropdownMenu.inMovement = true;
            $userProfileDropdownMenu.slideDown(400, function(){
                $userProfileDropdownMenu.inMovement = false;
            })
        }, function(){
            if ($userProfileDropdownMenu.inMovement) return;

            $userProfileDropdownMenu.inMovement = true;
            $userProfileDropdownMenu.slideUp(450, function(){
                $userProfileDropdownMenu.inMovement = false;
            })
        } );

//        $userProfileDropdownMenu.inMovement = false;

//        $userProfileLink.mouseenter(function(){
//            if ($userProfileDropdownMenu.inMovement) return;

//            $userProfileDropdownMenu.inMovement = true;
//            $userProfileDropdownMenu.slideDown(function(){
//                $userProfileDropdownMenu.inMovement = false;
//            })
//        }).mouseleave(function(){
//            if ($userProfileDropdownMenu.inMovement) return;

//            $userProfileDropdownMenu.inMovement = true;
//            $userProfileDropdownMenu.slideUp(function(){
//                $userProfileDropdownMenu.inMovement = false;
//            })
//        });

        $contentArea.find("[data-check-toggle]").click(function(e){
            e.stopPropagation();

            var $this = $(this);

            var inputName = $this.attr("data-check-toggle");

            var $selectedInputCheckboxes = $this.parents("form").find("[name='" + inputName + "']")
            // $this.is(':checked')
            var checked = this.checked;

            $selectedInputCheckboxes.each(function(){
                this.checked = checked;
            });
        });

        var PAGE_LOADED_COMPLETED = 'statechangecomplete';


        function loadPage(pageName, dataUrl){        
            if (dataUrl){
		        // Set Loading
		        $webmail.addClass('loading');

		        // Start Fade Out
		        // Animating to opacity to 0 still keeps the element's height intact
		        // Which prevents that annoying pop bang issue when loading in new content
		        $contentArea.animate({opacity:0},800);

		        // Ajax Request the Traditional Page
		        $.ajax({
			        url: dataUrl,
			        success: function(data, textStatus, jqXHR){
			            $webmail.removeClass('loading');
			            $global.trigger(PAGE_LOADED_COMPLETED);

                        var html = renderTemplate(templateName, data.context);
                        $contentArea.html(html);
                    },
			        error: function(jqXHR, textStatus, errorThrown){ 
			            $webmail.removeClass('loading');
			            $global.trigger(PAGE_LOADED_COMPLETED);

				        alert("Error loading page");
				        return false;
			        }
		        }); // end ajax

            } else {
                var html = renderTemplate(templateName);
                $contentArea.html(html);
            }
        }

        var slideout = new Slideout({
            'panel': document.getElementById('webmail-interior'),
            'menu': document.getElementById('mobile-menu'),
            'padding': 220,
            'tolerance': 70
        });

        var slideoutOpenSetting = WEBMAIL_SESSION_ID+"slideoutOpen";

        var isSlideoutOpen = global.localStorage.getItem(slideoutOpenSetting) === "1";
        if (isSlideoutOpen){
            slideout._opened = true;
            slideout._translateXTo(slideout._translateTo);
            global.document.documentElement.classList.add('slideout-open');
        }

        // Toggle button
        document.querySelectorAll('.toggle-mobile-menu').forEach(function(el){
            el.addEventListener('click', function() {
                slideout.toggle();
                global.localStorage.setItem(slideoutOpenSetting, slideout.isOpen() === true ? "1": "");
            })
        });


        $global.resize(function(){
            if (slideout.isOpen()){
                  slideout._translateXTo(0);
                  slideout._opened = false;
                  global.document.documentElement.classList.remove('slideout-open');
                  global.localStorage.setItem(slideoutOpenSetting, "");
            }
        });

        $(".mailbox-select-on-change").change(function(){
            var mbox = $(this).find("option:selected").val();
            var mailbox_url = reverse_url('show_folder', {
                "folder_name": 'inbox',
                "mbox": mbox
            });
            document.location.href= mailbox_url;
        });

        $(".go-back[href='#']").click(function(e){
            e.preventDefault();
            history.back();
        });

        document.querySelectorAll("input[type=password] + .show-password-link").forEach(function(passwordRevealerLink){
            var passwordRevealer = new PasswordRevealer(passwordRevealerLink.previousElementSibling, passwordRevealerLink, {
                onTriggerAction: function(isRevealed, toggleEl){
                    var toggleText;

                    if (isRevealed){
                        toggleText = _("Hide");
                    } else {
                        toggleText = _("Show");
                    }

                    toggleEl.innerText = toggleText;
                }
            })
            passwordRevealer.init();
        });

        init_page(PAGE_NAME, PAGE_CONTEXT_DATA);
    });

})(this); // end closure
