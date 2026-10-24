from src.analysis.radar_chart import RadarChart

radar = RadarChart()

financial_data = radar.load_financial_ratios()

print("=" * 70)
print("GENERATING RADAR CHARTS")
print("=" * 70)

count = 0

for company_id in financial_data.keys():

    try:

        radar.generate_radar_chart(company_id)

        count += 1

    except Exception as e:

        print(f"{company_id} : {e}")

print("=" * 70)
print(f"Generated {count} Radar Charts")
print("=" * 70)

radar.close()