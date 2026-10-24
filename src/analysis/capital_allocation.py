class CapitalAllocation:

    @staticmethod
    def classify(cfo, investing, financing):
        """
        Classify a company's capital allocation pattern.

        CFO        : Cash Flow from Operating Activities
        Investing : Cash Flow from Investing Activities
        Financing : Cash Flow from Financing Activities
        """

        if cfo is None or investing is None or financing is None:
            return "INSUFFICIENT_DATA"

        cfo_positive = cfo >= 0
        investing_positive = investing >= 0
        financing_positive = financing >= 0

        # (+, -, -)
        if cfo_positive and not investing_positive and not financing_positive:
            return "Reinvestor"

        # (+, +, -)
        if cfo_positive and investing_positive and not financing_positive:
            return "Shareholder Returns"

        # (+, +, +)
        if cfo_positive and investing_positive and financing_positive:
            return "Cash Accumulator"

        # (-, -, +)
        if not cfo_positive and not investing_positive and financing_positive:
            return "Growth Funded by Debt"

        # (-, +, +)
        if not cfo_positive and investing_positive and financing_positive:
            return "Distress"

        # (+, -, +)
        if cfo_positive and not investing_positive and financing_positive:
            return "Expansion Phase"

        # (-, -, -)
        if not cfo_positive and not investing_positive and not financing_positive:
            return "Pre-Revenue"

        return "Mixed"
