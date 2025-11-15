class UserFormatter:
    @staticmethod
    def format_user_name(first_name, last_name):
        return f"{first_name.strip().title()} {last_name.strip().title()}"

    @staticmethod
    def format_email(email):
        return email.strip().lower()

    @staticmethod
    def capitalize_name(first_name, last_name):
        return first_name.capitalize(), last_name.capitalize()

    @staticmethod
    def check_strong_password(password):
        import re
        if (len(password) < 8 or
            not re.search(r"[A-Z]", password) or
            not re.search(r"[a-z]", password) or
            not re.search(r"[0-9]", password) or
            not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)):
            return False
        return True

    @staticmethod
    def format_phone_number(phone_number):
        import re
        digits = re.sub(r"\D", "", phone_number)
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return phone_number
