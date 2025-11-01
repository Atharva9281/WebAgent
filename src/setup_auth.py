"""
One-time authentication setup for Linear and Notion
Saves browser sessions for reuse by the agent

Usage:
    python src/setup_auth.py
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os
import sys


def _launch_manual_context(p, profile_name: str):
    """Launch Chrome with reduced automation fingerprints using a persistent profile."""
    os.makedirs("auth", exist_ok=True)
    profile_dir = os.path.join("auth", profile_name)
    context = p.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=False,
        channel="chrome",
        viewport={"width": 1920, "height": 1080},
        args=[
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
        ],
        ignore_default_args=["--enable-automation"],
    )
    context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = window.chrome || {};
        window.chrome.runtime = window.chrome.runtime || {};
        """
    )
    return context


def setup_linear_auth():
    """Login to Linear manually and save session"""
    print("\n" + "=" * 70)
    print("🔐 LINEAR AUTHENTICATION SETUP")
    print("=" * 70)

    with sync_playwright() as p:
        # Launch visible Chrome browser
        context = _launch_manual_context(p, "linear_profile")
        page = context.new_page()

        try:
            # Navigate to Linear
            print("\n📍 Opening Linear login page...")
            page.goto("https://linear.app/login", timeout=30000)

            # Wait for manual login
            print("\n" + "-" * 70)
            print("⏳ PLEASE LOGIN MANUALLY IN THE BROWSER WINDOW")
            print("-" * 70)
            print("\nSteps:")
            print("  1. Enter your email/password OR use SSO")
            print("  2. Complete any 2FA if required")
            print("  3. Wait until you see your Linear workspace")
            print("  4. You should see the sidebar with projects/issues")
            print("\n" + "-" * 70)

            input("\n✅ Press ENTER after you're fully logged in and see your workspace...")

            # Verify login successful
            print("\n🔍 Verifying login...")
            page.goto("https://linear.app", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                print("⚠️  Linear page took too long to fully load; checking URL anyway.")

            # Check if actually logged in (look for sidebar or workspace elements)
            try:
                # Wait for any element that indicates we're logged in
                page.wait_for_timeout(2000)  # Give page time to load

                # Check current URL - if still on login page, failed
                current_url = page.url
                if "login" in current_url.lower():
                    print("\n❌ Still on login page - please try again")
                    context.close()
                    return False

                print("✅ Login verified!")

            except Exception as e:
                print(f"\n⚠️  Could not verify login automatically: {e}")
                print("Continuing anyway - if you're logged in, this should work")

            # Save authenticated state
            os.makedirs("auth", exist_ok=True)
            context.storage_state(path="auth/linear_session.json")

            print("\n" + "=" * 70)
            print("✅ LINEAR SESSION SAVED: auth/linear_session.json")
            print("=" * 70)

            context.close()
            return True

        except Exception as e:
            print(f"\n❌ Error during Linear setup: {e}")
            context.close()
            return False


def setup_notion_auth():
    """Login to Notion manually and save session"""
    print("\n" + "=" * 70)
    print("🔐 NOTION AUTHENTICATION SETUP")
    print("=" * 70)

    with sync_playwright() as p:
        # Launch visible Chrome browser
        context = _launch_manual_context(p, "notion_profile")
        page = context.new_page()

        try:
            # Navigate to Notion
            print("\n📍 Opening Notion login page...")
            page.goto("https://www.notion.so/login", timeout=30000)

            # Wait for manual login
            print("\n" + "-" * 70)
            print("⏳ PLEASE LOGIN MANUALLY IN THE BROWSER WINDOW")
            print("-" * 70)
            print("\nSteps:")
            print("  1. Enter your email and click 'Continue with email'")
            print("  2. Enter password OR use Google/Apple sign-in")
            print("  3. Wait until you see your Notion workspace")
            print("  4. You should see your pages in the sidebar")
            print("\n" + "-" * 70)

            input("\n✅ Press ENTER after you're fully logged in and see your workspace...")

            # Verify login
            print("\n🔍 Verifying login...")
            page.goto("https://www.notion.so", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                print("⚠️  Notion page took too long to fully load; checking URL anyway.")

            try:
                # Give page time to load
                page.wait_for_timeout(2000)

                # Check if still on login page
                current_url = page.url
                if "login" in current_url.lower():
                    print("\n❌ Still on login page - please try again")
                    context.close()
                    return False

                print("✅ Login verified!")

            except Exception as e:
                print(f"\n⚠️  Could not verify login automatically: {e}")
                print("Continuing anyway - if you're logged in, this should work")

            # Save authenticated state
            os.makedirs("auth", exist_ok=True)
            context.storage_state(path="auth/notion_session.json")

            print("\n" + "=" * 70)
            print("✅ NOTION SESSION SAVED: auth/notion_session.json")
            print("=" * 70)

            context.close()
            return True

        except Exception as e:
            print(f"\n❌ Error during Notion setup: {e}")
            context.close()
            return False


def verify_sessions():
    """Test that saved sessions work"""
    print("\n" + "=" * 70)
    print("🧪 VERIFYING SAVED SESSIONS")
    print("=" * 70)

    linear_exists = os.path.exists("auth/linear_session.json")
    notion_exists = os.path.exists("auth/notion_session.json")

    if not linear_exists and not notion_exists:
        print("\n❌ No sessions found. Please run the setup first.")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome")

        # Test Linear
        if linear_exists:
            print("\n📍 Testing Linear session...")
            try:
                context = browser.new_context(storage_state="auth/linear_session.json")
                page = context.new_page()
                page.goto("https://linear.app", timeout=30000)
                page.wait_for_load_state("networkidle", timeout=10000)

                # Check if still logged in
                current_url = page.url
                if "login" in current_url.lower():
                    print("❌ Linear session expired - please run setup again")
                else:
                    print("✅ Linear session works!")

                context.close()

            except Exception as e:
                print(f"❌ Linear session test failed: {e}")

        # Test Notion
        if notion_exists:
            print("\n📍 Testing Notion session...")
            try:
                context = browser.new_context(storage_state="auth/notion_session.json")
                page = context.new_page()
                page.goto("https://www.notion.so", timeout=30000)
                page.wait_for_load_state("networkidle", timeout=10000)

                # Check if still logged in
                current_url = page.url
                if "login" in current_url.lower():
                    print("❌ Notion session expired - please run setup again")
                else:
                    print("✅ Notion session works!")

                context.close()

            except Exception as e:
                print(f"❌ Notion session test failed: {e}")

        browser.close()

    return True


def main():
    """Main setup flow"""
    print("\n" + "=" * 70)
    print("🚀 WEB AGENT AUTHENTICATION SETUP")
    print("=" * 70)
    print("\nThis script will help you save authenticated sessions for:")
    print("  • Linear (project management)")
    print("  • Notion (workspace)")
    print("\nYou'll login manually in a Chrome window, then we save the session.")
    print("The agent can then reuse these sessions without needing to login again.")

    # Check if sessions already exist
    linear_exists = os.path.exists("auth/linear_session.json")
    notion_exists = os.path.exists("auth/notion_session.json")

    if linear_exists or notion_exists:
        print("\n⚠️  Existing sessions found:")
        if linear_exists:
            print("  • Linear: auth/linear_session.json")
        if notion_exists:
            print("  • Notion: auth/notion_session.json")

        response = input("\nOverwrite existing sessions? (y/n): ").lower().strip()
        if response != "y":
            print("\n✅ Keeping existing sessions. Use --verify to test them.")
            return

    # Setup Linear
    print("\n" + "=" * 70)
    print("STEP 1 OF 2: LINEAR")
    print("=" * 70)
    linear_success = setup_linear_auth()

    if not linear_success:
        print("\n❌ Linear setup failed. Please try again.")
        sys.exit(1)

    # Small pause between setups
    input("\n✅ Linear done! Press ENTER to continue to Notion setup...")

    # Setup Notion
    print("\n" + "=" * 70)
    print("STEP 2 OF 2: NOTION")
    print("=" * 70)
    notion_success = setup_notion_auth()

    if not notion_success:
        print("\n❌ Notion setup failed. Please try again.")
        sys.exit(1)

    # Verify both work
    print("\n" + "=" * 70)
    print("VERIFYING SESSIONS")
    print("=" * 70)
    verify_sessions()

    print("\n" + "=" * 70)
    print("✅ SETUP COMPLETE!")
    print("=" * 70)
    print("\nSaved sessions:")
    print("  • auth/linear_session.json")
    print("  • auth/notion_session.json")
    print("\n⚠️  SECURITY: Never commit these files to git!")
    print("   (They're automatically ignored by .gitignore)")
    print("\nNext step: Run the agent")
    print("  python src/agent.py")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Check for verify flag
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_sessions()
    else:
        main()
