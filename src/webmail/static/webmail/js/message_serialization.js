function stringToByteArray(s){
    var sUTF8 = unescape(encodeURIComponent(s));
    var len = sUTF8.length

    var array = new Uint8Array(len);
    for(var i = 0; i < len; i++) {
        array[i] = sUTF8.charCodeAt(i);
    }
    return array.buffer
}

function byteArrayToString(bytearray){
    var byteView = new Uint8Array(bytearray);

    var len = byteView.length;

    var sUTF8 = ''
    for (var i = 0; i < len; i++) {
        sUTF8 += String.fromCharCode(byteView[i])
    }

    var s = decodeURIComponent(escape(sUTF8))
    return s
}

function arrayBufferConcat(/* arraybuffers */) {
    var arrays = [].slice.call(arguments)


    var arrayBuffer = arrays.reduce(function(cbuf, buf, i) {
      if (i === 0) return cbuf

      var tmp = new Uint8Array(cbuf.byteLength + buf.byteLength)
      tmp.set(new Uint8Array(cbuf), 0)
      tmp.set(new Uint8Array(buf), cbuf.byteLength)

      return tmp.buffer
    }, arrays[0])

    return arrayBuffer
}

function createUint8BinaryData(d){
    var dataView = new DataView(new ArrayBuffer(Uint8Array.BYTES_PER_ELEMENT))
    dataView.setUint8(0, d);

    return dataView.buffer;
}

function createUint32BinaryData(d){
    var dataView = new DataView(new ArrayBuffer(Uint32Array.BYTES_PER_ELEMENT))
    dataView.setUint32(0, d);

    return dataView.buffer;
}


// attachmentFileName, attachmentFileData
function serializeMessage(subject, content, attachmentList){
    var subjectField = stringToByteArray(subject)
    var subjectLengthField = createUint8BinaryData(subjectField.byteLength)

    var contentField = stringToByteArray(content)
    var contentLengthField = createUint32BinaryData(contentField.byteLength)

    var messageFields = [subjectLengthField, subjectField, contentLengthField, contentField];

    if (attachmentList){
        var numAttachmentsField = createUint8BinaryData(attachmentList.length)
        messageFields.push(numAttachmentsField)

        attachmentList.forEach(function(attachment){
            var attachmentFileNameField = stringToByteArray(attachment.name)
            var attachmentFileNameLengthField = createUint8BinaryData(attachmentFileNameField.byteLength)
            
            var attachmentFileDataLength = createUint32BinaryData(attachment.fileData.byteLength)

            messageFields.push(attachmentFileNameLengthField, attachmentFileNameField, attachmentFileDataLength, attachment.fileData)
        });
    }

    return arrayBufferConcat.apply(null, messageFields);
}

function unserializeMessage(buffer){
    var index = 0;

    var dataView = new DataView(buffer);
    var subjectLength = dataView.getUint8(index);

    index += Uint8Array.BYTES_PER_ELEMENT;
    var subject = byteArrayToString(buffer.slice(index, index + subjectLength));

    index += subjectLength;

    var contentLength = dataView.getUint32(index);

    index += Uint32Array.BYTES_PER_ELEMENT;
 
    var content = byteArrayToString(buffer.slice(index, index + contentLength));

    index += contentLength;

    message = {
        "subject": subject,
        "content": content
    }

    if (index !== buffer.byteLength){
        var attachments = [];

        var numAttachments = dataView.getUint8(index)
        index += Uint8Array.BYTES_PER_ELEMENT;

        for (var i =0; i < numAttachments; i ++){
            var fileNameLength = dataView.getUint8(index);

            index += Uint8Array.BYTES_PER_ELEMENT;
            var name = byteArrayToString(buffer.slice(index, index + fileNameLength));

            index += fileNameLength;

            var fileDataLength = dataView.getUint32(index);

            index += Uint32Array.BYTES_PER_ELEMENT;

            var fileData = buffer.slice(index, index + fileDataLength);

            index += fileDataLength;

            attachments.push({
                name: name,
                fileData: fileData
            })
        }

        if (index !== buffer.byteLength){
            throw Error("Wrong serialization")
        }

        message.attachments = attachments;
    }

    return message
}
