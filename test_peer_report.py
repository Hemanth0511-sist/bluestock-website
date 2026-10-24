from src.comparison.peer_report import PeerReport


report = PeerReport()

try:

    report.create_sheets()

    report.save()

finally:

    report.close()