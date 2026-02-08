try:
    from playwright.sync_api import sync_playwright

    print("Playwright module found.")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
