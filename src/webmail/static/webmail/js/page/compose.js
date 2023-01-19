function compose_page_init(data){
    function is_valid_email(input) {
        return is_valid_email.emailRegExp.test(input)
    }

    is_valid_email.emailRegExp = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i;


    function make_timestamp(dateObj) {
        if (!dateObj) dateObj = new Date();

        var t = +dateObj + (window.tsOffset || 0)
        return t
    }

    function format_time(dateObj, addSeconds){
        if (!dateObj) dateObj = new Date();

		var h = dateObj.getHours();
		var m = dateObj.getMinutes();

		m = m < 10 ? "0" + m : m;

        var formatted_time = h + ":" + m

        if (addSeconds){
            var s = dateObj.getSeconds();
		    s = s < 10 ? "0" + s : s;

            formatted_time += ":" + s;
        }

        return formatted_time;
    }

    function humanize_bytes(bytes){
        return bytes;
    }

    var AUTOSAVE_DELAY = data.autodraft_save_delay || 1000;

    function DraftManager(keySuffix, subjectInputEl, toInputEl, ccInputEl, bccInputEl, draftSavedEl, editor){
        this.localStorageKey = "draft" + keySuffix;

        this.subjectInputEl = subjectInputEl;
        this.toInputEl = toInputEl;
        this.ccInputEl = ccInputEl;
        this.bccInputEl = bccInputEl;
        this.draftSavedEl = draftSavedEl;
        this.editor = editor;

        this.autosaveStarted = false;
    }

    DraftManager.prototype.clear = function(){
        localStorage.removeItem(this.localStorageKey);
        this.draftSavedEl.innerHTML = "";
    }

    DraftManager.prototype.removeData = function(){
        localStorage.removeItem(this.localStorageKey);
    }

    DraftManager.prototype.getDateSavedDraft = function(){
        var draftData = this.loadStoredData();
        if (!draftData) return;

        var date = new Date(draftData.timestamp);
        return date;
    }

    DraftManager.prototype.saveDraft = function(){
        var body = this.editor.value();

		var d = new Date();

        var timestamp = make_timestamp(d)

        var subject = this.subjectInputEl.value;
        var to = this.toInputEl.value;
        var cc = this.ccInputEl.value;
        var bcc = this.bccInputEl.value;

        if (subject === "" && to === "" && cc === "" && bcc === "" && body === ""){
            this.deleteStoredData();
            return;
        }

        var draftData = {
            "subject": subject,
            "to": to,
            "cc": cc,
            "bcc": bcc,
            "body": body,
            "timestamp": timestamp
        }

        if (this.ccInputEl)
            draftData.cc = this.ccInputEl.value;

        if (this.bccInputEl)
            draftData.bcc = this.bccInputEl.value;

        var value = JSON.stringify(draftData);

        localStorage.setItem(this.localStorageKey, value);

        var formatted_time = format_time(d, true);

		this.draftSavedEl.innerHTML = data.saved_draft_at + formatted_time;
    }

    DraftManager.prototype.stopAutosave = function(){
        if (!this.autosaveStarted) return;

        this.autosaveStarted = false;

        clearTimeout(this.autosaveTimeoutId);
        this.autosaveTimeoutId = null;
        this.editor.off("change", this._onChangeEditor);
    }

    DraftManager.prototype.startAutosave = function(){
        if (this.autosaveStarted) return;
        this.autosaveStarted = true;

		this.editor.codemirror.on("change", this._onChangeEditor.bind(this));
    }

    DraftManager.prototype._onChangeEditor = function(){
        var that = this;

        if (this.autosaveTimeoutId !== null){
            clearTimeout(this.autosaveTimeoutId);
        }

        this.autosaveTimeoutId = setTimeout(function() {
            that.saveDraft();
        }, AUTOSAVE_DELAY);
	}

    DraftManager.prototype.restore = function(){
        var draftData = this.loadStoredData();
        if (!draftData) return;

        if (draftData.subject) subjectInputEl.value = draftData.subject;

        if (draftData.to) {
            toInputEl.value = draftData.to;
            $(toInputEl).data("tagator").refresh()
        }

        if (draftData.cc) {
            ccInputEl.value = draftData.cc;
            $(ccInputEl).data("tagator").refresh()
        }

        if (draftData.bcc) {
            bccInputEl.value = draftData.bcc;
            $(bccInputEl).data("tagator").refresh()
        }

        this.editor.codemirror.setValue(draftData.body);
    }

    DraftManager.prototype.hasStoredData = function(){
        return localStorage.getItem(this.localStorageKey) !== null;
    }

    DraftManager.prototype.deleteStoredData = function(){
        localStorage.removeItem(this.localStorageKey);
    }

    DraftManager.prototype.loadStoredData = function(){
        var value = localStorage.getItem(this.localStorageKey)
        if (value == null) return;

        var draftData = JSON.parse(value);
        return draftData;
    }


    $(function(){
        var fileId = 0;
        var attachments = [];
        var $attachmentsListFormArea = $("#attachments-list-form-area");
        var $attachmentList = $attachmentsListFormArea.find("#attachment-list-management");

        var subjectInputEl = document.getElementById("subject");
        var toInputEl = document.getElementById("to");
        var ccInputEl = document.getElementById("cc");
        var bccInputEl = document.getElementById("bcc");

        var editor = new SimpleMDE({
            element: document.getElementById("editor-textarea")
        });

        var draftSavedEl = document.querySelector("#editor .editor-statusbar .autosave");

        var draftManager = new DraftManager(WEBMAIL_SESSION_ID, subjectInputEl, toInputEl, ccInputEl, bccInputEl, draftSavedEl, editor);
        if (draftManager.hasStoredData()){
            var $restoreDraftModal = $('#restore-draft-modal');
            var d = draftManager.getDateSavedDraft();
            var formatted_time = format_time(d, true);

            $restoreDraftModal.find(".time").text(formatted_time);

            $restoreDraftModal.find("button.restore-draft-modal-yes-btn").click(function(){
                draftManager.restore();
                $restoreDraftModal.modal('hide');
            });

            $restoreDraftModal.find("button.restore-draft-modal-clear-draft-btn").click(function(){
                draftManager.deleteStoredData();
                $restoreDraftModal.modal('hide');
            });

            $restoreDraftModal.modal('show');
        }

        if (data.auto_drafts){
            draftManager.startAutosave();
        }

        $(toInputEl).tagator({
            autocomplete: data.contact_emails,
            validator: is_valid_email
        });

        if (ccInputEl)
            $(ccInputEl).tagator({
                autocomplete: data.contact_emails,
                validator: is_valid_email
            });

        if (bccInputEl)
            $(bccInputEl).tagator({
                autocomplete: data.contact_emails,
                validator: is_valid_email
            });


        $(".tagator_element").each(function(i, el){
            var $tagator_element = $(el);
            var $input_element = $tagator_element.find(".tagator_input");
            //var $tagator_placeholder = $tagator_element.find(".tagator_placeholder");


            $input_element.bind('focus', function(){
                $tagator_element.addClass("tagator_element-focus");
                //$placeholder_element.hide();
            });

            $input_element.bind('blur', function(){
                $tagator_element.removeClass("tagator_element-focus");

                /*
                if ($tags_element.is(':empty') && !$input_element.val() && $source_element.attr('placeholder')) {
                    $placeholder_element.html($source_element.attr('placeholder'));
                    $placeholder_element.show();
		        }*/
            });
        });


        var uploadFile = function(opts) {
            var formData = new FormData();
            formData.append(opts.paramName, opts.file);

            var xhr = new XMLHttpRequest();

            if(opts.progress) {
                xhr.upload.addEventListener('progress', function(evt) {
                    if(evt.lengthComputable) {
                        var percentComplete = 100.0 * evt.loaded / evt.total;
                        opts.progress(percentComplete);
                    }
                }, false);
            }

            xhr.onload = function(evt) {
                // Fire the success/error handlers with the returned JSON
                var data = JSON.parse(xhr.responseText);
                if(data.ok) {
                    if(opts.onSuccess) {
                        opts.onSuccess(data);
                    }
                }
                else {
                    if(opts.onError) {
                        opts.onError(data);
                    }
                }
            };

            xhr.open('POST', opts.url, true);            
            xhr.setRequestHeader("X-CSRFToken", CSRF_MIDDLEWARE_TOKEN);
            xhr.send(formData);
        };

        // document.getElementById("id_file").value = "";
        var attachmentForm = document.getElementById("attachment_form");
        attachmentForm.reset();

        $('#attachment_file_input').change(function(e){
            $attachmentsListFormArea.removeClass("d-none");

            var file = this.files[0];
            attachments.push({
                "id": fileId,
                "file": file
            });

            $attachmentList.append("<li data-attachment-id=" + fileId + ">"+ file.name + " (" + humanize_bytes(file.size) + " bytes) <button class='icon-btn delete-attachment'><i class='fa fa-trash'></i></button></li>");
            fileId++;

            attachmentForm.reset();
        });

        $attachmentList.on("click", "button.delete-attachment", function(e){
            e.preventDefault();

            var $target = $(e.target);
            var fileId = $target.closest("li").data("attachment-id");

            var fileIndex = attachments.findIndex(function(fileItem){
                if (fileItem.id === fileId) return true;
            });

            if (fileIndex !== -1){
                attachments.splice(fileIndex, 1)
            }

            if (attachments.length === 0) $attachmentsListFormArea.addClass("d-none");

            $target.closest("li").remove();
            return false;
        });

        function sendAttachments(opts){
            console.log("sending attachmens here", opts.url)
            var numUploadedAttachments = 0;

            function onSuccess(data){
                numUploadedAttachments += 1;
                if (numUploadedAttachments === attachments.length) {
                    opts.onComplete();
                } else {
                    uploadFile({
                        url: opts.url,
                        paramName: 'attachment',
                        file: opts.attachments[numUploadedAttachments].file,
                        onSuccess: onSuccess,
                        onError: opts.onUploadAttachmentError
                    })
                }
            }

            uploadFile({
                url: opts.url,
                paramName: 'attachment',
                file: opts.attachments[0].file,
                onSuccess: onSuccess,
                onError: opts.onUploadAttachmentError
            });
        }

        function sendMessage(subject, to, cc, bcc, body, attachments, callback, errback){      
            var formData = new FormData();
            formData.append("subject", subject);
            formData.append("to", to);
            formData.append("cc", cc);
            formData.append("bcc", bcc);
            formData.append("body", body);
            formData.append("has_attachments", attachments.length === 0? "": "1");

            var xhr = new XMLHttpRequest();

            xhr.onload = function(evt) {
                // Fire the success/error handlers with the returned JSON
                var response = JSON.parse(xhr.responseText);

                if(response.ok) {
                    if(attachments.length !== 0){
                        var data = response.data;
                        sendAttachments({
                            url: data.attachment_upload_url,
                            attachments: attachments,
                            onComplete: function(){
                                var xhr = new XMLHttpRequest();

                                xhr.onload = function(evt) {
                                    var response = JSON.parse(xhr.responseText);

                                    if(response.ok) {
                                        callback();
                                    } else {
                                        console.log(response);
                                    }
                                }

                                xhr.open('POST', data.finnished_attachments_session_url, true);            
                                xhr.setRequestHeader("X-CSRFToken", CSRF_MIDDLEWARE_TOKEN);
                                xhr.send(null);
                            },
                            onUploadAttachmentError: console.log
                        });
                    } else {
                        callback();
                    }
                } else {
                    errback(response);
                }
            };

            xhr.open('POST', data.mail_send_url, true);
            xhr.setRequestHeader("X-CSRFToken", CSRF_MIDDLEWARE_TOKEN);

            xhr.send(formData);
        }

        var resetAttachmentState = function(){
            $attachmentList.empty();
            attachments = [];
            fileId = 0;
        }

        if (data.mail_send_url) {
            $('#send_email_btn').click(function(e){
                e.preventDefault();

                var subject = subjectInputEl.value;
                var to = toInputEl.value;
                var cc = ccInputEl === null? null: ccInputEl.value;
                var bcc = bccInputEl === null? null: bccInputEl.value;
                var body = editor.value();

                sendMessage(subject, to, cc, bcc, body, attachments, function(){
                    draftManager.clear();

                    $("#content-area").html(data.message_sent_html);
                }, function(response){
                    console.log(response);

                    Object.keys(response.error_data).forEach(function(key){
                        $('<span class="form-field-error">' + response.error_data[key] + '</span><br>').insertAfter("#tagator_"+key);
                    });

                    document.scrollingElement.scrollTop = 0;
                });
            });
        }


        $('#save_draft_btn').click(function(e){
            draftManager.saveDraft();
            notifier.show(null, data.draft_saved_text, "success", null, true, 2200)
            return false
        });

        $('#clear_draft_btn').click(function(e){
            e.preventDefault();

            if (draftManager.hasStoredData()){
                draftManager.clear();
                notifier.show(null, data.draft_cleared_text, "success", null, true, 2200);
            } else {
                notifier.show(null, data.no_data_saved_in_draft_text, "warning", null, true, 2200);
            }

            return false
        });

        $('#discard_btn').click(function(e){
            e.preventDefault();

            draftManager.removeData();
            window.location.href = $(this).data("url");
        });
    });
}
