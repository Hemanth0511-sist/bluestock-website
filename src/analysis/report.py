class ValidationReport:

    def __init__(self):
        self.total = 0
        self.valid = 0
        self.invalid = 0

    def add(self, ratios):

        self.total += 1

        if ratios is None:
            self.invalid += 1
        else:
            self.valid += 1

    def summary(self):

        print("\n========== Validation Report ==========")
        print(f"Companies Processed : {self.total}")
        print(f"Valid Companies     : {self.valid}")
        print(f"Invalid Companies   : {self.invalid}")

        if self.total > 0:
            accuracy = (self.valid / self.total) * 100
            print(f"Success Rate        : {accuracy:.2f}%")

        print("=======================================\n")
