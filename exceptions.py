class FormFillerException(Exception):
    default_message = "Backend error"
    default_status_code = 400

    def __init__(self, message=None, status_code=None):
        self.message = message or self.default_message
        self.status_code = status_code or self.default_status_code
