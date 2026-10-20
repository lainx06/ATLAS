"""Try It Live. Hosted: one live session per visitor session (`atlas.hosted.page`). Local: run
a project, or open a recorded run read-only (`atlas.ui.local_page`)."""

from atlas import hosted

if hosted.enabled():
    from atlas.hosted import page

    page.live_page()
else:
    from atlas.ui import local_page

    local_page.main()
