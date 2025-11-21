"""Quick check if Airflow is installed"""
import sys

try:
    import airflow
    print("✅ Airflow IS installed")
    try:
        print(f"   Version: {airflow.__version__}")
    except:
        print("   Version: Unknown")
    sys.exit(0)
except ImportError:
    print("❌ Airflow is NOT installed")
    print("\n💡 Solution: Use the standalone script instead:")
    print("   python orbit_agentic_dashboard_local.py --limit 3")
    sys.exit(1)

