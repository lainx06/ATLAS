"""The ATLAS browser UI (T-07): a Streamlit front end over the unchanged engine.

The UI only starts engine runs (`atlas.audit.audit`, `atlas.agent.controller.run_agent` with a
`FixtureClient`) and displays the artifacts they write. It computes no outcome, rebuilds no
diff and never executes project code itself. See docs/UI_SPEC.md.
"""
