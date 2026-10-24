class FinancialValidator:

    @staticmethod
    def is_valid_number(value):
        """
        Check whether the value is usable for calculations.
        """
        return value is not None and isinstance(value, (int, float))

    @staticmethod
    def is_positive(value):
        """
        Check whether the value is greater than zero.
        """
        return FinancialValidator.is_valid_number(value) and value > 0

    @staticmethod
    def validate_ratio(value):

        if value is None:
            return False

        if isinstance(value, (int, float)):
            return True

        return False
