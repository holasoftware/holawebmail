from django.template import Library
from django.contrib.messages import constants as message_constants


from webmail.webmail_url_utils import reverse_webmail_url, add_query_string


register = Library()


def handle_url_read_mail(mbox, message_id, read=None, starred=None, has_attachments=None):
    query_params = {}

    if read == True:
        query_params["read"] = "1"
    elif read == False:
        query_params["read"] = "0"

    if starred == True:
        query_params["starred"] = "1"
    elif starred == False:
        query_params["starred"] = "0"

    if has_attachments == True:
        query_params["has_attachments"] = "1"
    elif has_attachments == False:
        query_params["has_attachments"] = "0"

    url = reverse_webmail_url("read_mail", mbox, kwargs={"message_id": message_id}, query_params=query_params)

    return url

def handle_url_compose(mbox, to=None):
    if to is not None:
        query_params = {
            "to": to
        }
    else:
        query_params = None

    url = reverse_webmail_url("compose", mbox, query_params=query_params)
    return url

def handle_url_mails_bulk_action(mbox, folder_name):
    url = reverse_webmail_url("mails_bulk_action", mbox, kwargs={"folder_name": folder_name})
    return url

def handle_url_add_star(mbox, message_id):
    url = reverse_webmail_url("add_star", mbox, kwargs={"message_id": message_id})
    return url

def handle_url_remove_star(mbox, message_id):
    url = reverse_webmail_url("remove_star", mbox, kwargs={"message_id": message_id})
    return url

def handle_url_mail_send(mbox):
    url = reverse_webmail_url("mail_send", mbox)
    return url

def handle_url_reply(mbox, message_id):
    url = reverse_webmail_url("reply", mbox, kwargs={"message_id": message_id})
    return url

def handle_url_reply_all(mbox, message_id):
    url = reverse_webmail_url("reply_all", mbox, kwargs={"message_id": message_id})
    return url

def handle_url_forward_email(mbox, message_id):
    url = reverse_webmail_url("forward_email", mbox, kwargs={"message_id": message_id})
    return url

def handle_url_mark_as_read(mbox, message_id):
    url = reverse_webmail_url("mark_as_read", mbox, kwargs={"message_id": message_id})
    return url

def handle_url_mark_as_unread(mbox, message_id):
    url = reverse_webmail_url("mark_as_unread", mbox, kwargs={"message_id": message_id})
    return url

def handle_url_mail_delete(mbox, message_id):
    url = reverse_webmail_url("mail_delete", mbox, kwargs={"message_id": message_id})
    return url

def handle_url_show_folder(mbox, folder_name, read=None, starred=None, has_attachments=None, page=None):
    query_params = {}

    if read == True:
        query_params["read"] = "1"
    elif read == False:
        query_params["read"] = "0"

    if starred == True:
        query_params["starred"] = "1"
    elif starred == False:
        query_params["starred"] = "0"

    if has_attachments == True:
        query_params["has_attachments"] = "1"
    elif has_attachments == False:
        query_params["has_attachments"] = "0"

    if page is not None:
        query_params["page"] = page

    url = reverse_webmail_url("show_folder", mbox, kwargs={"folder_name": folder_name}, query_params=query_params)

    return url

def handle_url_edit_obj(mbox, object_name=None, obj_id=None):
    object_id_key = object_name + "_id"

    url = reverse_webmail_url(object_name + "_edit", mbox, kwargs={
        object_id_key: obj_id
    })

    return url


url_handlers = {
    "show_folder": handle_url_show_folder, 
    "read_mail": handle_url_read_mail,
    "edit_obj": handle_url_edit_obj,
    "compose": handle_url_compose,
    "mails_bulk_action": handle_url_mails_bulk_action,
    "add_star": handle_url_add_star,
    "remove_star": handle_url_remove_star,
    "mail_send": handle_url_mail_send,
    "reply": handle_url_reply,
    "reply_all": handle_url_reply_all,
    "forward_email": handle_url_forward_email,
    "mark_as_read": handle_url_mark_as_read,
    "mark_as_unread": handle_url_mark_as_unread,
    "mail_delete": handle_url_mail_delete
}


@register.simple_tag(takes_context=True)
def mail_url(context, name, **extra):
    if "mbox" in extra:
        mbox = extra.pop("mbox")
    else:
        mbox = context.get("mbox", None)

    if name in url_handlers:
        url = url_handlers[name](mbox, **extra)
    else:
        url = reverse_webmail_url(name, mbox, kwargs=extra)

    return url


@register.simple_tag(takes_context=True)
def pagination_url(context, mbox=None, page="1"):
    if mbox is None:
        mbox = context.get("mbox", None)

    query_params = {
        "page": str(page)
    }

    if mbox is not None:
        query_params["mbox"] = mbox

    request = context["request"]
    url = request.path + add_query_string("", query_params)

    return url


MESSAGE_LEVEL_CLASSES = {
    message_constants.DEBUG: "alert alert-warning",
    message_constants.INFO: "alert alert-info",
    message_constants.SUCCESS: "alert alert-success",
    message_constants.WARNING: "alert alert-warning",
    message_constants.ERROR: "alert alert-danger",
}


@register.filter
def bootstrap_message_classes(message):
    """Return the message classes for a message."""
    extra_tags = None
    try:
        extra_tags = message.extra_tags
    except AttributeError:
        pass
    if not extra_tags:
        extra_tags = ""
    classes = [extra_tags]
    try:
        level = message.level
    except AttributeError:
        pass
    else:
        try:
            classes.append(MESSAGE_LEVEL_CLASSES[level])
        except KeyError:
            classes.append("alert alert-danger")
    return " ".join(classes).strip()


