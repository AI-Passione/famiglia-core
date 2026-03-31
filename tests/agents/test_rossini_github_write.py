import os
from dotenv import load_dotenv
load_dotenv()
from famiglia_core.agents.rossini import Rossini
from famiglia_core.agents.llm.client import client

def verify_rossini_github():
    print("Testing Dr. Rossini's GitHub capabilities locally...")
    rossini = Rossini()
    
    # Assert tools are in the registry
    assert "manage_github_issue" in rossini.tools
    assert "manage_github_pull_request" in rossini.tools
    assert "manage_github_milestone" in rossini.tools
    assert "list_accessible_repos" in rossini.tools
    
    # Check capabilities status text
    caps = rossini.check_capabilities()
    print("\n--- Capabilities Status ---")
    print(caps)
    
    # Let's verify the tools don't throw an error when called directly (expecting mock or failure due to no real repo, but the method signature is correct)
    print("\n--- Mock Testing Tool Signature ---\n")
    try:
        res = rossini.manage_github_issue("la-passione-inc/test", action="read", title="1")
        print(res)
    except Exception as e:
        print(f"Error calling manage_github_issue: {e}")

    # For manual testing, you'd run this to ensure no parsing/import errors on init
    print("\n✅ Registration successful.")

if __name__ == "__main__":
    verify_rossini_github()
