"""Copy the selected third-party skills from pinned upstream commits (playbook Section 22.2).

Content is read from the pinned commit objects (`git show <sha>:<path>`), not from the
clone's working tree, so a moved clone cannot change what is installed. Existing files
are never overwritten: identical files are skipped, differing files abort the run.

Prerequisite (ignored clones):
  git clone https://github.com/mattpocock/skills.git .dev/skill-sources/matt
  git clone https://github.com/addyosmani/agent-skills.git .dev/skill-sources/addy

Run:   uv run --locked python scripts/sync_skills.py          (install missing files)
       uv run --locked python scripts/sync_skills.py --check  (verify only; no writes)
"""

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / ".dev" / "skill-sources"
DEST_ROOTS = [ROOT / ".claude", ROOT / ".agents"]

# source key -> (canonical URL, pinned commit). Update only by deliberate revalidation.
PINS = {
    "matt": (
        "https://github.com/mattpocock/skills.git",
        "49dd158d1076134a641b33efb035946536778336",
    ),
    "addy": (
        "https://github.com/addyosmani/agent-skills.git",
        "aeac41d4d005999432bb7312f7ff06383a91d59d",
    ),
}

# (source key, upstream skill folder). Each lands at <dest>/skills/<folder name>/.
SKILLS = [
    ("matt", "skills/engineering/setup-matt-pocock-skills"),
    ("matt", "skills/engineering/grill-with-docs"),
    ("matt", "skills/productivity/grilling"),  # called by grill-with-docs
    ("matt", "skills/engineering/domain-modeling"),  # called by grill-with-docs
    ("matt", "skills/engineering/to-spec"),
    ("addy", "skills/code-review-and-quality"),
    ("addy", "skills/debugging-and-error-recovery"),
    ("addy", "skills/test-driven-development"),
]

# Shared files cited as ../../references/<file> from a skill folder; placing them at
# <dest>/references/ makes those paths resolve without editing SKILL.md.
SHARED = [
    ("addy", "references/security-checklist.md"),  # code-review-and-quality
    ("addy", "references/performance-checklist.md"),  # code-review-and-quality
    ("addy", "references/testing-patterns.md"),  # test-driven-development
]


def git(key: str, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(SOURCES / key), *args], check=True, capture_output=True
    ).stdout


def planned_files() -> dict[str, bytes]:
    """Map destination-relative path -> pinned blob bytes."""
    plan: dict[str, bytes] = {}
    for key, (_, sha) in PINS.items():
        git(
            key, "cat-file", "-e", f"{sha}^{{commit}}"
        )  # pinned commit must exist locally
    for key, folder in SKILLS:
        sha = PINS[key][1]
        name = folder.rsplit("/", 1)[1]
        listing = git(key, "ls-tree", "-r", "--name-only", sha, "--", folder).decode()
        for path in listing.splitlines():
            plan[f"skills/{name}/{path[len(folder) + 1 :]}"] = git(
                key, "show", f"{sha}:{path}"
            )
        # MIT requires the notice to travel with each copy.
        plan[f"skills/{name}/LICENSE"] = git(key, "show", f"{sha}:LICENSE")
    for key, path in SHARED:
        plan[path] = git(key, "show", f"{PINS[key][1]}:{path}")
    plan["references/LICENSE"] = git("addy", "show", f"{PINS['addy'][1]}:LICENSE")
    return plan


def conflicts(plan: dict[str, bytes]) -> list[str]:
    """Existing files that differ from the pin, or foreign files in a managed skill folder."""
    found = []
    managed = {rel.split("/")[1] for rel in plan if rel.startswith("skills/")}
    for dest in DEST_ROOTS:
        for rel, data in sorted(plan.items()):
            target = dest / rel
            if target.exists() and target.read_bytes() != data:
                found.append(f"DIFFERS  {target.relative_to(ROOT)}")
        for name in sorted(managed):
            for extra in (dest / "skills" / name).rglob("*"):
                if extra.is_file() and extra.relative_to(dest).as_posix() not in plan:
                    found.append(f"EXTRA    {extra.relative_to(ROOT)}")
    return found


def main() -> int:
    check_only = "--check" in sys.argv[1:]
    plan = planned_files()
    problems = conflicts(plan)
    if problems and not check_only:
        print("\n".join(problems))
        print("Refusing to write: existing files would be overwritten or merged.")
        return 1
    for dest in DEST_ROOTS:
        for rel, data in sorted(plan.items()):
            target = dest / rel
            if target.exists():
                continue
            if check_only:
                problems.append(f"MISSING  {target.relative_to(ROOT)}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            print(f"WROTE    {target.relative_to(ROOT)}")
    print("\n".join(problems))
    for rel, data in sorted(plan.items()):
        print(f"{hashlib.sha256(data).hexdigest()[:16]}  {rel}")
    print(
        f"{len(plan)} files x {len(DEST_ROOTS)} destinations; problems: {len(problems)}"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
