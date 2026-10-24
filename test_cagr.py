from src.analysis.cagr import CAGR

print(CAGR.calculate(100, 200, 5))
print(CAGR.calculate(0, 200, 5))
print(CAGR.calculate(-100, 200, 5))
print(CAGR.calculate(100, -50, 5))
print(CAGR.calculate(-100, -50, 5))
print(CAGR.calculate(None, 100, 5))