from src.comparison.comparison import CompanyComparison

comparison = CompanyComparison()

companies = [
    "TCS",
    "INFY",
    "HCLTECH"
]

result = comparison.compare_companies(companies)

comparison.display_comparison(result)

comparison.highlight_best(result)

comparison.overall_winner(result)

comparison.close()