(function(global){
    var upload = function(file, settings) {
        var signal = $.Deferred();
        var formData = new FormData();
        formData.append('attachment', file);

        var xhr = new XMLHttpRequest();
        if(settings.progress) {
            xhr.upload.addEventListener('progress', function(evt) {
                if(evt.lengthComputable) {
                    var percentComplete = 100.0 * evt.loaded / evt.total;
                    settings.progress(percentComplete);
                }
            }, false);
        }

        xhr.onload = function(evt) {
            // Refresh the attachments listing
            refresh();

            // Fire the success/error handlers with the returned JSON
            var data = JSON.parse(xhr.responseText);
            if(data.ok) {
                if(settings.success) {
                    settings.success(data);
                }
                signal.resolve(data);
            }
            else {
                if(settings.error) {
                    settings.error(data);
                }
                signal.reject(data);
            }
        };

        xhr.open('POST', settings.url, true);
        xhr.send(formData);

        return signal;
    };

    // input.files
    var uploadFiles = function(files, settings) {
        var chain = null;
        // Call all the upload methods sequentially.
        for(var i = 0; i < input.files.length; i++) {
            chain = chain ? chain.then(upload(files[i], settings)) : upload(files[i], settings);
        }
        // Clear the file input, if it was used to trigger the upload.
        if(input) {
            resetInput(input);
        }
    };

    global.Uploader = {
        upload: upload,
        uploadFiles: uploadFiles
    }
})(this);
