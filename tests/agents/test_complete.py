from famiglia_core.agents.rossini import Rossini
r = Rossini()
# Mock the tool slightly to avoid waiting for approval or github tokens if not needed,
# or just run it and let it fail on 404, we just want to see the Turn 2 output.
res = r.complete_task("could u list out all Github Issues u see in la-passione-inc/test?", sender="Jimmy", on_intermediate_response=lambda x: print("INTER:", x))
print("FINAL RESULT FROM COMPLETE_TASK:")
print(res)
