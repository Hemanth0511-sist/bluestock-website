from src.analysis.capital_allocation import CapitalAllocation

tests = [
    (100, -50, -25),
    (100, 40, -10),
    (100, 30, 20),
    (-20, -40, 50),
    (-10, 20, 30),
    (120, -30, 50),
    (-10, -20, -30),
    (10, -5, 0),
]

for cfo, investing, financing in tests:
    result = CapitalAllocation.classify(
        cfo,
        investing,
        financing
    )

    print(
        f"CFO={cfo}, "
        f"Investing={investing}, "
        f"Financing={financing} "
        f"=> {result}"
    )