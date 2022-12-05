#class AJAXError(Exception):
#    def __init__(self, error_data=None, msg='Ajax error'):
#        self.error_data = error_data

#        super().__init__(msg)



class AJAXError(Exception):
    error_code=None
    error_description=None

    def __init__(self, error_description=None, error_code=None, error_data=None):
        if error_code is not None:
            self.error_code = error_code

        if error_description is not None:
            self.error_description = error_description

        self.error_data = error_data

        if self.error_description is not None:
            super().__init__(self.error_description)
        else:
            super().__init__()


class InvalidAjaxRequest(AJAXError):
    error_code = "invalid_request"
    error_description = "Invalid request"


class FormAJAXError(AJAXError):
    def __init__(self, form, form_name=None):
        if form_name is None:
            form_name  = form.__class__.__name__

        error_description = "Error in form validation of '%s'" % form_name

        super().__init__(error_code="form_errors", error_description=error_description, error_data=form.errors)

